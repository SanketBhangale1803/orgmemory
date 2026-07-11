"""Tests for the intelligence layer: trust, drift, correlation, simulation,
blast radius. Everything runs against real ingested evidence through the
standard pipeline — no fixtures that bypass ingestion."""

import json

from app.agentgate_adapter import AgentGateAdapter
from app.audit import AuditService
from app.core.database import connect
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.intelligence import DriftService, SimulationService, blast_radius, correlate_changes
from app.intelligence.trust import detect_contradictions, trust_score
from app.runbooks import RunbookService


def _services(graph):
    hcag = HCAGAdapter(graph)
    audit = AuditService()
    ingestion = IngestionService(graph, hcag, audit)
    runbooks = RunbookService(graph, hcag, audit)
    return hcag, audit, ingestion, runbooks


INCIDENT = (
    "reddit_service failed because KAFKA_BOOTSTRAP_SERVERS pointed at the wrong listener.\n"
    "- Inspect reddit_service logs with docker logs reddit_service.\n"
    "- Restart reddit_service with docker restart reddit_service."
)


def test_trust_score_reflects_evidence_breadth(graph):
    hcag, _, ingestion, _ = _services(graph)
    project_id = ingestion.create_project("Trust")
    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    ingestion.ingest_item(
        project_id,
        "github_issue",
        "Issue #42: reddit_service Kafka timeout",
        "reddit_service cannot reach kafka:9092. Root cause: KAFKA_BOOTSTRAP_SERVERS mismatch.",
    )
    evidence = hcag.retrieve_context(project_id, "why is reddit_service failing?")
    result = trust_score(project_id, evidence)
    assert 0 < result["score"] <= 1
    assert result["level"] in {"high", "medium", "low"}
    assert result["factors"]["recency_basis"] == "ingestion_time"
    assert "distinct source" in result["reason"]
    # Empty evidence must yield zero trust, not a default score.
    empty = trust_score(project_id, [])
    assert empty["score"] == 0.0 and empty["level"] == "none"


def test_contradiction_detection_flags_disjoint_causes(graph):
    hcag, _, ingestion, _ = _services(graph)
    project_id = ingestion.create_project("Contradictions")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Postmortem A",
        "payment_service outage. Root cause: DATABASE_URL was rotated without redeploy.",
    )
    ingestion.ingest_item(
        project_id,
        "slack",
        "Thread B",
        "payment_service outage was caused by REDIS_HOST pointing at the old cluster.",
    )
    evidence = hcag.retrieve_context(project_id, "why did payment_service fail?")
    contradictions = detect_contradictions(evidence)
    assert contradictions, "disjoint cause tokens from different sources should conflict"
    pair = contradictions[0]
    assert pair["source_a"] != pair["source_b"]


def test_drift_fresh_then_stale_when_source_removed(graph):
    hcag, audit, ingestion, runbooks = _services(graph)
    project_id = ingestion.create_project("Drift")
    result = ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    extracted = runbooks.extract(project_id, "reddit_service kafka failure recovery")
    assert extracted["runbooks_created"] == 1
    record_id = extracted["runbooks"][0]["record_id"]

    drift = DriftService(graph, runbooks, hcag, audit)
    fresh = drift.check_runbook(record_id, project_id)
    assert fresh["drift_status"] == "fresh"

    with connect() as conn:
        conn.execute("DELETE FROM knowledge_items WHERE id=?", (result["item_id"],))
    stale = drift.check_runbook(record_id, project_id)
    assert stale["drift_status"] == "stale"
    assert any(signal["type"] == "source_missing" for signal in stale["signals"])


def test_drift_project_rollup(graph):
    hcag, audit, ingestion, runbooks = _services(graph)
    project_id = ingestion.create_project("Drift rollup")
    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    runbooks.extract(project_id, "reddit_service kafka failure recovery")
    drift = DriftService(graph, runbooks, hcag, audit)
    rollup = drift.check_project(project_id)
    assert rollup["runbooks_checked"] == 1
    assert rollup["stale"] == 0


def test_change_correlation_ranks_overlapping_pr(graph):
    hcag, _, ingestion, _ = _services(graph)
    project_id = ingestion.create_project("Correlation")
    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    ingestion.ingest_item(
        project_id,
        "pull_request",
        "PR #128: update compose listeners",
        "Modified docker-compose.yml and changed KAFKA_BOOTSTRAP_SERVERS for reddit_service.",
        "https://github.com/org/repo/pull/128",
    )
    ingestion.ingest_item(
        project_id,
        "pull_request",
        "PR #130: docs typo fix",
        "Fixed a typo in CONTRIBUTING.md.",
        "https://github.com/org/repo/pull/130",
    )
    evidence = hcag.retrieve_context(project_id, "why is reddit_service failing?")
    correlation = correlate_changes(project_id, evidence, "reddit_service")
    assert correlation["suspects"], "the overlapping PR must be flagged"
    top = correlation["suspects"][0]
    assert top["title"].startswith("PR #128")
    assert "KAFKA_BOOTSTRAP_SERVERS" in top["shared_env_vars"]
    titles = [suspect["title"] for suspect in correlation["suspects"]]
    assert "PR #130: docs typo fix" not in titles
    assert correlation["recency_basis"] == "ingestion_order"


def test_simulation_gates_dangerous_steps(graph):
    hcag, audit, ingestion, runbooks = _services(graph)
    project_id = ingestion.create_project("Simulation")
    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    extracted = runbooks.extract(project_id, "reddit_service kafka failure recovery")
    record_id = extracted["runbooks"][0]["record_id"]

    simulation = SimulationService(runbooks, AgentGateAdapter(), audit)
    result = simulation.simulate(project_id, runbook_id=record_id, environment="production")
    assert result["verdict"] == "blocked_without_approvals"
    assert result["approvals_required"]
    assert result["dangerous_steps"]
    assert all(step["would_execute"] is False for step in result["steps"])
    restart = next(step for step in result["steps"] if "restart" in step["description"].lower())
    assert restart["approval_required"] is True


def test_simulation_by_scenario_and_honest_no_match(graph):
    hcag, audit, ingestion, runbooks = _services(graph)
    project_id = ingestion.create_project("Simulation scenario")
    simulation = SimulationService(runbooks, AgentGateAdapter(), audit)
    empty = simulation.simulate(project_id, scenario="Simulate Kafka outage for reddit_service")
    assert empty["verdict"] == "no_applicable_runbook"
    assert empty["applicable_runbook"] is None

    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    runbooks.extract(project_id, "reddit_service kafka failure recovery")
    matched = simulation.simulate(project_id, scenario="Simulate Kafka outage for reddit_service")
    assert matched["applicable_runbook"] is not None
    assert "reddit_service" in json.dumps(matched["applicable_runbook"]).lower() or matched["steps"]


def test_blast_radius_uses_only_graph_edges(graph):
    hcag, _, ingestion, _ = _services(graph)
    project_id = ingestion.create_project("Blast radius")
    for name in ("reddit_service", "kafka", "api_gateway_service"):
        graph.upsert_service({"id": f"{project_id}:{name}", "project_id": project_id, "name": name})
    graph.link(
        "SERVICE_DEPENDS_ON_SERVICE",
        "Service",
        f"{project_id}:reddit_service",
        "Service",
        f"{project_id}:kafka",
    )
    graph.link(
        "SERVICE_DEPENDS_ON_SERVICE",
        "Service",
        f"{project_id}:api_gateway_service",
        "Service",
        f"{project_id}:reddit_service",
    )
    result = blast_radius(graph, project_id, "reddit_service")
    assert result["dependencies"] == ["kafka"]
    assert result["direct_dependents"] == ["api_gateway_service"]
    assert result["basis"] == "graph_edges_only"
    assert any("api_gateway_service" in line for line in result["impact_statements"])

    unknown = blast_radius(graph, project_id, "ghost_service")
    assert unknown["direct_dependents"] == []
    assert any("unknown, not zero" in line for line in unknown["impact_statements"])


def test_runbook_versioning_bumps_only_on_change(graph):
    hcag, _, ingestion, runbooks = _services(graph)
    project_id = ingestion.create_project("Versioning")
    ingestion.ingest_item(project_id, "incident", "Kafka incident", INCIDENT)
    first = runbooks.extract(project_id, "reddit_service kafka failure recovery")
    assert first["runbooks"][0]["version"] == 1

    # Re-extraction over identical evidence must not bump the version.
    second = runbooks.extract(project_id, "reddit_service kafka failure recovery")
    assert second["runbooks"][0]["version"] == 1

    # New evidence that adds a step changes the content and bumps the version.
    ingestion.ingest_item(
        project_id,
        "incident",
        "Kafka incident follow-up",
        "reddit_service kafka failure follow-up.\n- Verify KAFKA_BOOTSTRAP_SERVERS matches the deployed compose file.",
    )
    third = runbooks.extract(project_id, "reddit_service kafka failure recovery")
    assert third["runbooks"][0]["version"] == 2
    assert len(third["runbooks"][0]["versions"]) == 2
