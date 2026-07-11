from __future__ import annotations

import app.retrieval.service as retrieval_service
from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.hcag_adapter.models import RouteResult
from app.ingestion import IngestionService
from app.retrieval import RetrievalService
from app.retrieval.hypotheses import extract_hypotheses
from app.retrieval.service import should_run_diagnostics


def _route(service_name: str | None, subdomain: str) -> RouteResult:
    return RouteResult(
        domain="engineering_operations",
        subdomain=subdomain,
        context_window=f"engineering_operations.{subdomain}",
        query_type="diagnostic",
        service_name=service_name,
        boundary_type="none",
        confidence=0.8,
    )


def test_gate_only_fires_for_low_confidence_service_incidents():
    incident = _route("reddit_service", "incident_response")
    # Low confidence on a service incident -> diagnose.
    assert should_run_diagnostics(incident, sufficient=True, confidence=0.3) is True
    # Insufficient evidence on a service incident -> diagnose even if confidence number is high.
    assert should_run_diagnostics(incident, sufficient=False, confidence=0.9) is True
    # Confident, sufficient service-incident answer -> normal path, no diagnosis.
    assert should_run_diagnostics(incident, sufficient=True, confidence=0.8) is False
    # Out of scope: non-incident subdomain and missing service.
    assert should_run_diagnostics(_route("reddit_service", "ci_cd"), False, 0.1) is False
    assert should_run_diagnostics(_route(None, "incident_response"), False, 0.1) is False


def test_hypotheses_discriminate_between_contradictory_causes(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())

    upstream_project = ingestion.create_project("Upstream cause")
    config_project = ingestion.create_project("Config cause")
    ingestion.ingest_item(
        upstream_project,
        "incident",
        "Incident A",
        "reddit_service failed because Kafka broker kafka:9092 refused connections.",
    )
    ingestion.ingest_item(
        config_project,
        "incident",
        "Incident B",
        "reddit_service failed because DATABASE_URL was missing during boot.",
    )

    evidence_a = hcag.retrieve_context(
        upstream_project, "why is reddit_service failing?", "reddit_service"
    )
    evidence_b = hcag.retrieve_context(
        config_project, "why is reddit_service failing?", "reddit_service"
    )
    hyp_a = extract_hypotheses(graph, upstream_project, "reddit_service", evidence_a)
    hyp_b = extract_hypotheses(graph, config_project, "reddit_service", evidence_b)

    categories_a = {item["category"] for item in hyp_a}
    categories_b = {item["category"] for item in hyp_b}

    # Scenario A implicates the upstream dependency (kafka); scenario B does not.
    assert "upstream_dependency" in categories_a
    assert "upstream_dependency" not in categories_b
    upstream = next(item for item in hyp_a if item["category"] == "upstream_dependency")
    assert "kafka" in upstream["signals"]

    # Scenario B implicates configuration (DATABASE_URL); scenario A does not.
    assert "configuration" in categories_b
    assert "configuration" not in categories_a
    config = next(item for item in hyp_b if item["category"] == "configuration")
    assert "DATABASE_URL" in config["signals"]

    # Every hypothesis carries real supporting evidence nodes and an honest prior basis.
    for hypothesis in hyp_a + hyp_b:
        assert hypothesis["supporting_evidence"]
        assert hypothesis["evidence_count"] >= 1
        assert hypothesis["weight"] > 0
        assert hypothesis["prior_basis"] == "ingestion_recency_weighted_evidence_count"


def test_ask_adds_hypotheses_only_on_diagnostic_path(graph, monkeypatch):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Diagnostic path")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Incident",
        "reddit_service failed because Kafka broker kafka:9092 refused connections.",
    )
    retrieval = RetrievalService(hcag, AuditService())

    # Force the low-confidence path so the additive field is exercised deterministically.
    monkeypatch.setattr(retrieval_service, "LOW_CONFIDENCE_THRESHOLD", 1.0)
    incident = retrieval.ask(project_id, "@runbook why is reddit_service failing?")
    assert "hypotheses" in incident
    assert any(item["category"] == "upstream_dependency" for item in incident["hypotheses"])

    # A non-incident (overview) query is out of scope -> contract unchanged, no field.
    overview = retrieval.ask(project_id, "@runbook what is this project about?")
    assert "hypotheses" not in overview


def test_ask_normal_path_contract_unchanged(graph, monkeypatch):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Normal path")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Incident",
        "reddit_service failed because Kafka broker kafka:9092 refused connections.",
    )
    retrieval = RetrievalService(hcag, AuditService())

    # Threshold of 0.0 means a sufficient answer never trips the confidence gate.
    monkeypatch.setattr(retrieval_service, "LOW_CONFIDENCE_THRESHOLD", 0.0)
    result = retrieval.ask(project_id, "@runbook why is reddit_service failing?")
    if result["confidence"] > 0 and result["evidence"]:
        assert "hypotheses" not in result
