import pytest

from app.audit import AuditService
from app.core.config import settings
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory import BeliefStore, ChangeIntelligenceService, interpret_diff
from app.memory.change_intelligence import OpenAIStructuredChangeProvider

ENTRA_DIFF = """diff --git a/src/main.jsx b/src/main.jsx
--- a/src/main.jsx
+++ b/src/main.jsx
@@ -12,8 +12,8 @@
-const employeeDirectory = localEmployeeFixture;
-const employee = employeeDirectory.find(item => item.id === employeeId);
+const entraIdClient = createEntraIdClient();
+const employee = await entraIdClient.getUser(ssoClaims.employeeId);
"""


def _project(graph):
    return IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Entra migration", "https://github.com/acme/identity-app.git"
    )


def _seed_beliefs(graph, project_id):
    store = BeliefStore(graph)
    scope = {"project": project_id, "repo": "acme/identity-app"}
    source = {
        "type": "repo_file",
        "id": "file:src/main.jsx@old",
        "timestamp": "2026-07-20T10:00:00Z",
        "confidence": 0.95,
    }
    identity = store.create(
        project_id,
        "employee identity source",
        "Employee identity comes from a local employee directory fixture.",
        confidence=0.93,
        scope=scope,
        authority_tier="current_code_config",
        source=source,
    )
    fixture = store.create(
        project_id,
        "local employee directory fixture",
        "The application uses a local employee directory fixture.",
        confidence=0.92,
        scope=scope,
        authority_tier="current_code_config",
        source=source,
    )
    return store, identity, fixture


def test_interpret_diff_extracts_entra_identity_change_without_storage(graph):
    extracted = interpret_diff(
        ENTRA_DIFF,
        {"scope": {"repo": "acme/identity-app"}},
        llm=lambda diff, context: {
            "summary": "Identity moved to Entra ID.",
            "added": [],
            "removed": [
                {
                    "claim": "local employee directory fixture",
                    "previous_value": "The application uses a local fixture.",
                    "current_value": "The local fixture is no longer authoritative.",
                    "confidence": 0.98,
                    "affected_areas": ["src/main.jsx"],
                    "agent_implication": "Do not edit the fixture.",
                }
            ],
            "modified": [],
            "affected_areas": ["src/main.jsx"],
            "agent_implications": ["Do not edit the fixture."],
        },
    )

    assert extracted.summary == "Identity moved to Entra ID."
    assert extracted.removed[0].claim == "local employee directory fixture"
    assert BeliefStore(graph).list_current("missing") == []


def test_entra_commit_updates_identity_invalidates_fixture_and_explains_agent_impact(graph):
    project_id = _project(graph)
    store, identity, fixture = _seed_beliefs(graph, project_id)
    service = ChangeIntelligenceService(graph)
    event, created = service.observe(
        project_id,
        "delivery-entra-1",
        "github_push",
        "acme/identity-app",
        "abc123",
        "https://github.com/acme/identity-app/commit/abc123",
        {"after": "abc123"},
    )

    result = service.process(event["id"], ENTRA_DIFF, {"scope": {"repo": "acme/identity-app"}})

    assert created is True
    assert result["status"] == "ready"
    assert result["result"]["counts"] == {
        "added": 1,
        "updated": 1,
        "invalidated": 1,
        "conflicts": 0,
    }
    current = store.get_current(
        project_id,
        "employee identity source",
        {"project": project_id, "repo": "acme/identity-app"},
    )
    assert "Microsoft Entra ID" in current["current_value"]
    assert "SSO claims" in current["current_value"]
    assert store.get(identity["id"])["status"] == "updated"
    assert store.get(fixture["id"])["status"] == "invalidated"
    assert (
        store.get_current(
            project_id,
            "local employee directory fixture",
            {"project": project_id, "repo": "acme/identity-app"},
        )
        is None
    )
    assert result["result"]["affected_areas"] == ["src/main.jsx"]
    assert "do not add employees" in result["result"]["agent_implications"][0]
    assert [stage["stage"] for stage in result["result"]["stage_history"]] == [
        "interpreting",
        "reconciling",
        "activating",
        "ready",
    ]
    belief_ids = {belief["id"] for belief in result["beliefs"]}
    assert identity["id"] in belief_ids
    assert fixture["id"] in belief_ids
    assert any(
        belief["current_value"].startswith("Employee identity comes from Microsoft Entra ID")
        for belief in result["beliefs"]
    )
    identity_provider = store.get_current(
        project_id,
        "identity provider",
        {"project": project_id, "repo": "acme/identity-app"},
    )
    assert identity_provider is not None
    assert (
        identity_provider["current_value"]
        == "The application's identity provider is Microsoft Entra ID."
    )


def test_replaying_semantic_change_delivery_is_idempotent(graph):
    project_id = _project(graph)
    store, _, _ = _seed_beliefs(graph, project_id)
    service = ChangeIntelligenceService(graph)
    first, created = service.observe(
        project_id,
        "delivery-replay",
        "github_push",
        "acme/identity-app",
        "abc123",
        "",
        {},
    )
    service.process(first["id"], ENTRA_DIFF, {"scope": {"repo": "acme/identity-app"}})
    replay, replay_created = service.observe(
        project_id,
        "delivery-replay",
        "github_push",
        "acme/identity-app",
        "abc123",
        "",
        {},
    )
    replayed_result = service.process(
        replay["id"], ENTRA_DIFF, {"scope": {"repo": "acme/identity-app"}}
    )

    assert created is True
    assert replay_created is False
    assert replay["id"] == first["id"]
    assert replayed_result["status"] == "ready"
    assert len(store.relationships(project_id, "UPDATES")) == 1
    assert len(store.relationships(project_id, "INVALIDATES")) == 1
    assert len(service.list(project_id)) == 1


def test_repeated_semantic_change_from_new_delivery_does_not_create_self_update(graph):
    project_id = _project(graph)
    store, _, _ = _seed_beliefs(graph, project_id)
    service = ChangeIntelligenceService(graph)
    first, _ = service.observe(
        project_id,
        "delivery-semantic-first",
        "github_push",
        "acme/identity-app",
        "abc123",
        "",
        {},
    )
    service.process(first["id"], ENTRA_DIFF, {"scope": {"repo": "acme/identity-app"}})
    repeated, _ = service.observe(
        project_id,
        "delivery-semantic-repeat",
        "github_push",
        "acme/identity-app",
        "def456",
        "",
        {},
    )
    result = service.process(repeated["id"], ENTRA_DIFF, {"scope": {"repo": "acme/identity-app"}})

    assert result["result"]["counts"]["updated"] == 0
    assert all(
        relationship["from_belief_id"] != relationship["to_belief_id"]
        for relationship in store.relationships(project_id)
    )


@pytest.mark.skipif(
    not settings.openai_api_key or not settings.org_memory_run_live_llm_tests,
    reason="Set OPENAI_API_KEY and ORG_MEMORY_RUN_LIVE_LLM_TESTS=true for the live contract test",
)
def test_live_model_returns_structured_entra_change_contract(graph):
    extracted = interpret_diff(
        ENTRA_DIFF,
        {"scope": {"repo": "acme/identity-app"}},
        llm=OpenAIStructuredChangeProvider(),
    )

    assert extracted.affected_areas
    assert extracted.modified or extracted.added
    assert all(0 <= item.confidence <= 1 for item in extracted.modified + extracted.added)
