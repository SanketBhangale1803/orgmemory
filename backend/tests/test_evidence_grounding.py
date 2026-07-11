from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService


def test_same_query_changes_with_ingested_evidence_and_always_cites(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    first = ingestion.create_project("First")
    second = ingestion.create_project("Second")
    ingestion.ingest_item(
        first,
        "incident",
        "Database incident",
        "payment_service failed. Root cause: the database connection pool was exhausted.\n- Inspect connection pool metrics.",
    )
    ingestion.ingest_item(
        second,
        "incident",
        "Certificate incident",
        "payment_service failed. Root cause: the upstream TLS certificate had expired.\n- Inspect the certificate expiry date.",
    )
    retrieval = RetrievalService(hcag)

    answer_one = retrieval.ask(first, "@runbook why is payment_service failing?")
    answer_two = retrieval.ask(second, "@runbook why is payment_service failing?")

    assert answer_one["answer"] != answer_two["answer"]
    assert "connection pool" in answer_one["answer"]
    assert "certificate" in answer_two["answer"]
    assert answer_one["evidence"] and answer_two["evidence"]
    assert all(
        citation["source_title"] for citation in answer_one["evidence"] + answer_two["evidence"]
    )


def test_insufficient_evidence_is_explicit_and_uncited(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Empty")
    response = RetrievalService(hcag).ask(project_id, "@runbook why is unknown_service failing?")
    assert response["answer"] == "I do not have enough evidence to answer this confidently."
    assert response["evidence"] == []


def test_generic_project_overview_uses_readme_evidence(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Acme", "https://github.com/example/acme")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        (
            "# Acme Scheduler\n\n"
            "Acme Scheduler is a healthcare appointment application designed for clinics. "
            "It features role-based access and calendar integration."
        ),
        source_id=f"file:{project_id}:README.md",
    )

    response = RetrievalService(hcag).ask(project_id, "@runbook what is this service about?")

    assert "healthcare appointment application" in response["answer"]
    assert response["evidence"]
    assert response["evidence"][0]["source_title"] == "README.md"
    assert response["likely_cause"].startswith("Not applicable")
