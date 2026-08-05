from app.audit import AuditService
from app.auth.app_auth import create_dev_session
from app.core.database import connect
from app.governance import ScopeService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory import CompanyBrainService, CompanyMemoryService
from app.retrieval import RetrievalService


def _workspace_project(graph, name="Company Brain"):
    session = create_dev_session("owner@company.test", "Owner")
    workspace_id = session["user"]["active_workspace_id"]
    ingestion = IngestionService(graph, HCAGAdapter(graph), AuditService())
    project_id = ingestion.create_project(name)
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO workspace_projects VALUES (?,?)",
            (workspace_id, project_id),
        )
    return session, workspace_id, project_id, ingestion


def test_source_revision_emits_memory_change_set_and_invalidates_artifact(graph):
    _, _, project_id, ingestion = _workspace_project(graph)
    first = ingestion.ingest_item(
        project_id,
        "report",
        "Media policy",
        "Production media must not be stored on the local filesystem.",
        source_id="policy:media",
    )
    brain = CompanyBrainService(graph)
    memory = CompanyMemoryService(graph).get(first["memory_unit_ids"][0])
    artifact = brain.save_artifact(
        project_id,
        "Agent media brief",
        "brief",
        "Agents must follow the current media policy.",
        ["policy:media"],
        [memory["id"]],
    )

    second = ingestion.ingest_item(
        project_id,
        "report",
        "Media policy",
        "Production media must be stored in MinIO instead of the local filesystem.",
        source_id="policy:media",
    )

    revisions = brain.list_revisions(project_id, "policy:media")
    assert [item["version"] for item in revisions] == [2, 1]
    assert second["change_set"]["conflicts"]
    refreshed = brain.artifact(artifact["id"])
    assert refreshed["status"] == "stale"
    assert refreshed["impacts"][0]["change_set_id"] == second["change_set"]["id"]


def test_team_scope_security_trims_memory_and_answer_context(graph):
    session, workspace_id, project_id, ingestion = _workspace_project(graph, "Scoped memory")
    scopes = ScopeService()
    platform = scopes.create_team(workspace_id, "Platform")
    finance = scopes.create_team(workspace_id, "Finance")
    scopes.add_member(platform["id"], session["user"]["id"])
    ingestion.ingest_item(
        project_id,
        "slack",
        "Private deployment decision",
        "The team decided production deploys must use the platform release workflow.",
        source_id="slack:private",
        metadata={"team_ids": [platform["id"]]},
    )

    memory_service = CompanyMemoryService(graph)
    assert memory_service.list(project_id, allowed_team_ids=[platform["id"]])
    assert memory_service.list(project_id, allowed_team_ids=[finance["id"]]) == []

    result = RetrievalService(HCAGAdapter(graph)).ask(
        project_id,
        "What was decided about production deploys?",
        principal={"id": "finance-agent"},
        allowed_team_ids=[finance["id"]],
    )
    assert result["memory_units"] == []
    assert result["evidence"] == []
    assert result["context_envelope"]["authorized_team_ids"] == [finance["id"]]


def test_skill_spec_is_versioned_and_becomes_stale_when_memory_changes(graph):
    _, _, project_id, ingestion = _workspace_project(graph, "Skill memory")
    first = ingestion.ingest_item(
        project_id,
        "doc",
        "Refund procedure",
        "Refund operators must verify the order before approval. Run `refund verify` before issuing payment.",
        source_id="doc:refunds",
    )
    brain = CompanyBrainService(graph)
    memories = CompanyMemoryService(graph).list(project_id, latest=True)
    skill = brain.compile_skill(project_id, "handle-refund", memories)
    assert skill["spec"]["evidence"] == ["doc:refunds"]
    assert skill["version"] == 1

    ingestion.ingest_item(
        project_id,
        "doc",
        "Refund procedure",
        "Refund operators must use the fraud review queue instead of `refund verify` before issuing payment.",
        source_id="doc:refunds",
    )
    assert brain.list_skills(project_id)[0]["status"] == "stale"
    assert first["source_revision"]["version"] == 1
