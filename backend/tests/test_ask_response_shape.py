"""The ask response must carry trust score, Slack relations, and explained
graph paths — and must not assert trust when evidence is insufficient."""

from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService


def test_ask_includes_trust_and_slack_relations(graph):
    hcag = HCAGAdapter(graph)
    audit = AuditService()
    ingestion = IngestionService(graph, hcag, audit)
    project_id = ingestion.create_project("Ask shape")
    ingestion.ingest_item(
        project_id,
        "incident",
        "Kafka postmortem",
        "reddit_service failed because KAFKA_BOOTSTRAP_SERVERS pointed at the wrong listener.",
    )
    ingestion.ingest_item(
        project_id,
        "slack",
        "#cosmos-platform: reddit_service down",
        "reddit_service is failing again, same kafka listener error as last month.",
        "https://slack.example/archives/C1/p1",
    )
    ingestion.ingest_item(
        project_id,
        "pull_request",
        "PR #128: change kafka listeners",
        "Changed KAFKA_BOOTSTRAP_SERVERS in docker-compose.yml for reddit_service.",
        "https://github.com/org/repo/pull/128",
    )
    retrieval = RetrievalService(hcag, audit)
    result = retrieval.ask(project_id, "@runbook why is reddit_service failing?")

    assert result["evidence"], "grounded answer requires citations"
    trust = result["trust_score"]
    assert 0 < trust["score"] <= 1
    assert trust["level"] in {"high", "medium", "low"}
    assert trust["reason"]
    assert result["related_slack_messages"], "slack evidence must surface as a relation"
    assert "graph_path_explanations" in result["retrieval_trace"]
    # Incident question with an overlapping ingested PR → correlation present.
    assert "change_correlation" in result
    assert result["change_correlation"]["suspects"][0]["title"].startswith("PR #128")


def test_ask_without_evidence_reports_no_trust(graph):
    hcag = HCAGAdapter(graph)
    audit = AuditService()
    ingestion = IngestionService(graph, hcag, audit)
    project_id = ingestion.create_project("Ask empty")
    retrieval = RetrievalService(hcag, audit)
    result = retrieval.ask(project_id, "@runbook why is billing_service failing?")
    assert result["answer"] == "I do not have enough company memory to answer this confidently."
    assert result["trust_score"]["score"] == 0.0
    assert result["trust_score"]["level"] == "none"
    assert result["related_slack_messages"] == []
