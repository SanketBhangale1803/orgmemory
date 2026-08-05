from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory import BeliefStore, ChangeIntelligenceService
from app.retrieval import RetrievalService

ENTRA_DIFF = """diff --git a/src/main.jsx b/src/main.jsx
--- a/src/main.jsx
+++ b/src/main.jsx
@@ -12,8 +12,8 @@
-const employeeDirectory = localEmployeeFixture;
-const employee = employeeDirectory.find(item => item.id === employeeId);
+const entraIdClient = createEntraIdClient();
+const employee = await entraIdClient.getUser(ssoClaims.employeeId);
"""


def test_policy_question_prefers_matching_atomic_memory_over_irrelevant_chunks(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP AI PRs")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "src/main.jsx",
        "setError('Employee ID was not found in the local directory fixture.');",
    )
    ingestion.ingest_item(
        project_id,
        "doc",
        "Media storage decision",
        (
            "The platform team decided Instagram media must be stored in MinIO.\n"
            "instagram_service depends on Kafka and MinIO.\n"
            "Production media must not be stored on the local filesystem."
        ),
        source_id="upload:media-policy",
    )

    response = RetrievalService(hcag).ask(
        project_id,
        "What is the current media-storage policy, what changed, and which source should an agent follow?",
    )

    assert "Instagram media must be stored in MinIO" in response["answer"]
    assert "must not be stored on the local filesystem" in response["answer"]
    # Says plainly that nothing changed, without naming graph relationship types.
    assert (
        "Nothing recorded. No source shows this was updated or contradicted." in response["answer"]
    )
    assert "UPDATES" not in response["answer"]
    assert "[Media storage decision]" in response["answer"]
    assert "Employee ID" not in response["answer"]
    assert response["memory_units"]
    assert {item["source_title"] for item in response["evidence"]} == {"Media storage decision"}


def test_unrelated_memory_does_not_override_evidence_retrieval(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Scoped memories")
    ingestion.ingest_item(
        project_id,
        "doc",
        "Media policy",
        "Production media must be stored in MinIO.",
        source_id="media",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        "This repository is a Python travel search service.",
        source_id="readme",
    )

    response = RetrievalService(hcag).ask(project_id, "What is this repository about?")

    assert "travel search service" in response["answer"]
    assert "Production media" not in response["answer"]


def test_semantic_change_question_uses_belief_history_instead_of_commit_metadata(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("SAP AI PRs", "https://github.com/acme/sap-ai-prs.git")
    scope = {"project": project_id, "repo": "acme/sap-ai-prs"}
    source = {
        "type": "repo_file",
        "id": "src/main.jsx@before-entra",
        "timestamp": "2026-07-20T10:00:00Z",
        "confidence": 0.95,
    }
    beliefs = BeliefStore(graph)
    beliefs.create(
        project_id,
        "employee identity source",
        "Employee identity comes from a local employee directory fixture.",
        confidence=0.93,
        scope=scope,
        authority_tier="current_code_config",
        source=source,
    )
    beliefs.create(
        project_id,
        "local employee directory fixture",
        "The application uses a local employee directory fixture.",
        confidence=0.92,
        scope=scope,
        authority_tier="current_code_config",
        source=source,
    )
    changes = ChangeIntelligenceService(graph)
    event, _ = changes.observe(
        project_id,
        "delivery-entra-ask",
        "github_push",
        "acme/sap-ai-prs",
        "b84352225282347b52d3fe83556b300de252791f",
        "https://github.com/acme/sap-ai-prs/commit/b8435222",
        {},
    )
    changes.process(event["id"], ENTRA_DIFF, {"scope": scope})

    response = RetrievalService(hcag).ask(
        project_id,
        (
            "What changed about employee identity in the latest commit? Explain what was "
            "true before, what is true now, which belief was invalidated, which files are "
            "affected, and what an AI coding agent should do differently. Cite the source evidence."
        ),
    )

    assert response["answer_kind"] == "semantic_change"
    assert "local employee directory fixture" in response["answer"]
    assert "Microsoft Entra ID" in response["answer"]
    assert "Invalidated belief" in response["answer"]
    assert "src/main.jsx" in response["answer"]
    assert "do not add employees" in response["answer"]
    assert "b8435222" in response["answer"]
    assert response["memory_units"]
    assert response["invalidations"]
    assert response["semantic_change"]["event_id"] == event["id"]
    assert response["evidence"][0]["source_url"].endswith("/commit/b8435222")
