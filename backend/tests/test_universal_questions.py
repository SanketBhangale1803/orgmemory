from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService


def _project(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Unseen questions")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "config/database.js",
        "MongoDB stores account records. Mongoose opens the connection using MONGODB_URI.",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "services/media.js",
        "Uploaded images are persisted in GridFS and their object IDs are stored with each post.",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "auth/passport.js",
        "Passport Local authenticates users with a server-side session cookie.",
    )
    return hcag, project_id


def test_unrecognized_question_is_answered_without_an_intent_handler(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id,
        "Which persistence technology holds account records, and where is that configured?",
    )

    assert result["answer_kind"] == "general"
    assert "MongoDB" in result["answer"]
    assert "MONGODB_URI" in result["answer"]
    assert {item["source_title"] for item in result["evidence"]} == {"config/database.js"}
    assert result["retrieval_trace"]["universal_query_plan"]["retrieval_queries"]


def test_multi_part_unknown_question_activates_multiple_context_facets(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id,
        "Describe how images are persisted, plus how users are authenticated.",
    )

    assert "GridFS" in result["answer"]
    assert "Passport Local" in result["answer"]
    assert {item["source_title"] for item in result["evidence"]} == {
        "services/media.js",
        "auth/passport.js",
    }
    assert "authentication" in result["retrieval_trace"]["universal_query_plan"]["facets"]


def test_unknown_question_still_abstains_when_the_subject_is_absent(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id, "Which billing vendor processes international card refunds?"
    )

    assert result["answer"] == "I do not have enough company memory to answer this confidently."
    assert result["confidence"] <= 0.25
    assert result["evidence"] == []


def test_missing_local_answer_automatically_activates_authorized_workspace_context(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    frontend = ingestion.create_project("Storefront")
    platform = ingestion.create_project("Data platform")
    ingestion.ingest_item(
        frontend,
        "repo_file",
        "README.md",
        "The storefront renders the customer account experience.",
    )
    ingestion.ingest_item(
        platform,
        "repo_file",
        "docs/audit-exports.md",
        "Company audit exports are retained in the compliance-archive S3 bucket for seven years.",
    )
    retrieval = RetrievalService(hcag)

    result = retrieval.ask(
        frontend,
        "Where are company audit exports retained?",
        workspace_project_ids=[frontend, platform],
    )

    assert "compliance-archive S3 bucket" in result["answer"]
    assert {item["project_id"] for item in result["evidence"]} == {platform}
    assert result["retrieval_trace"]["scope_mode"] == "workspace"

    local_only = retrieval.ask(
        frontend,
        "Where are audit exports retained in this repo?",
        workspace_project_ids=[frontend, platform],
    )
    assert local_only["answer"] == "I do not have enough company memory to answer this confidently."
