from app.audit import AuditService
from app.company_context import CompanyContextService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService


def test_hcag_context_survives_adapter_restart(graph):
    first_adapter = HCAGAdapter(graph)
    project_id = IngestionService(graph, first_adapter, AuditService()).create_project(
        "Persistent context"
    )

    first = first_adapter.route_query(project_id, "Why is reddit_service failing?")
    assert first.service_name == "reddit_service"
    assert first.query_count == 1
    assert first.plan["intent"] == "MULTI_HOP"

    restarted_adapter = HCAGAdapter(graph)
    follow_up = restarted_adapter.route_query(project_id, "What changed for it in production?")

    assert follow_up.service_name == "reddit_service"
    assert follow_up.context_reused is True
    assert follow_up.query_count == 2
    assert "active service: reddit_service" in follow_up.resolved_query
    assert restarted_adapter.engine.startswith("hcag_hybrid_memory_arcadedb_v3_")


def test_unrelated_query_does_not_inherit_service(graph):
    adapter = HCAGAdapter(graph)
    project_id = IngestionService(graph, adapter, AuditService()).create_project("Scoped context")
    adapter.route_query(project_id, "Why is payment_service failing?")

    unrelated = adapter.route_query(
        project_id,
        "Explain the authentication architecture and workspace membership authorization model",
    )

    assert unrelated.service_name is None
    assert unrelated.context_reused is False
    assert "active service" not in unrelated.resolved_query


def test_short_self_contained_question_clears_stale_service(graph):
    adapter = HCAGAdapter(graph)
    project_id = IngestionService(graph, adapter, AuditService()).create_project("Scope reset")
    adapter.route_query(project_id, "Why is reddit_service failing?")

    unrelated = adapter.route_query(project_id, "Who approves production restarts?")

    assert unrelated.service_name is None
    assert unrelated.context_reused is False
    assert adapter.context_store.get(project_id)["active_service"] == ""


def test_company_context_briefing_is_derived_from_real_state(graph):
    adapter = HCAGAdapter(graph)
    ingestion = IngestionService(graph, adapter, AuditService())
    project_id = ingestion.create_project("Context briefing", "/workspace/context-briefing")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Payments postmortem",
        "payment_service failed because DATABASE_URL was unavailable. Escalate to platform on-call.",
    )
    adapter.route_query(project_id, "Why is payment_service failing?")

    briefing = CompanyContextService(graph, adapter.context_store).briefing(project_id)

    assert briefing["project"]["name"] == "Context briefing"
    assert briefing["continuity"]["persisted"] is True
    assert briefing["continuity"]["active_service"] == "payment_service"
    assert briefing["knowledge"]["items"] == 1
    assert briefing["knowledge"]["context_window_count"] == 1
    assert briefing["knowledge"]["context_windows"][0]["item_count"] == 1
    assert briefing["coverage"]["checks"]["evidence_indexed"] is True
    assert briefing["coverage"]["meaning"].endswith("not a model accuracy claim.")
