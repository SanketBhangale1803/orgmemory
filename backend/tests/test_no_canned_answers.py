from pathlib import Path

from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService


def test_no_canned_answers_same_query_changes_with_sources(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    first = ingestion.create_project("First evidence")
    second = ingestion.create_project("Second evidence")
    ingestion.ingest_item(
        first,
        "incident",
        "Incident A",
        "reddit_service failed because Kafka broker kafka:9092 refused connections.",
    )
    ingestion.ingest_item(
        second,
        "incident",
        "Incident B",
        "reddit_service failed because DATABASE_URL was missing during boot.",
    )

    retrieval = RetrievalService(hcag, AuditService())
    answer_a = retrieval.ask(first, "@runbook why is reddit_service failing?")
    answer_b = retrieval.ask(second, "@runbook why is reddit_service failing?")

    assert answer_a["evidence"]
    assert answer_b["evidence"]
    assert answer_a["likely_cause"] != answer_b["likely_cause"]
    assert "kafka" in answer_a["answer"].lower()
    assert "database_url" in answer_b["answer"].lower()


def test_related_sources_derived_from_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Related sources")
    ingestion.ingest_item(
        project_id,
        "github_issue",
        "reddit_service crashes on Kafka timeout",
        "reddit_service fails because Kafka broker kafka:9092 refused the connection.",
        "https://github.com/org/repo/issues/42",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "services/reddit_service/consumer.py",
        "reddit_service consumer connects to kafka:9092 and times out without a retry.",
        "https://github.com/org/repo/blob/main/services/reddit_service/consumer.py",
    )

    result = RetrievalService(hcag, AuditService()).ask(
        project_id, "@runbook why is reddit_service failing?"
    )

    issue_urls = {item["url"] for item in result["related_issues"]}
    file_titles = {item["title"] for item in result["related_files"]}
    assert "https://github.com/org/repo/issues/42" in issue_urls
    assert "services/reddit_service/consumer.py" in file_titles
    # Nothing fabricated: every related item traces to an ingested source.
    assert result["related_pull_requests"] == []


def test_no_related_sources_without_evidence(graph):
    hcag = HCAGAdapter(graph)
    project_id = IngestionService(graph, hcag, AuditService()).create_project("Empty related")

    result = RetrievalService(hcag, AuditService()).ask(
        project_id, "@runbook why is reddit_service failing?"
    )

    assert result["related_files"] == []
    assert result["related_issues"] == []
    assert result["related_pull_requests"] == []


def test_no_confident_answer_without_evidence(graph):
    hcag = HCAGAdapter(graph)
    project_id = IngestionService(graph, hcag, AuditService()).create_project("Empty")

    result = RetrievalService(hcag, AuditService()).ask(
        project_id, "@runbook why is reddit_service failing?"
    )

    assert result["confidence"] <= 0.25
    assert result["evidence"] == []
    assert result["answer"] == "I do not have enough company memory to answer this confidently."


def test_no_hardcoded_service_response_path_present():
    source_files = [
        "app/retrieval/service.py",
        "app/retrieval/reasoner.py",
        "app/graph/arcadedb_store.py",
        "app/hcag_adapter/adapter.py",
    ]
    for relative in source_files:
        content = (Path(__file__).resolve().parents[1] / relative).read_text()
        assert 'if "reddit_service"' not in content
        assert "Kafka advertised listener mismatch" not in content
