from __future__ import annotations

import subprocess

from app.audit import AuditService
from app.core.database import row, rows
from app.graph import graph_ranker
from app.graph.graph_ranker import rank_records
from app.hcag_adapter import HCAGAdapter
from app.ingestion.extractors import chunk_document
from app.ingestion.maintenance import sanitize_existing_index
from app.ingestion.repository import RepositoryIngestor
from app.ingestion.service import IngestionService
from app.ingestion.slack import SlackIngestor
from app.reliability import OperationalAssertionService
from app.retrieval import RetrievalService


class _SemanticProvider:
    model_name = "test-semantic"
    semantic = True

    def embed_query(self, _: str) -> list[float]:
        return [1.0, 0.0]


class _Reranker:
    model_name = "test-cross-encoder"

    def score(self, _: str, documents: list[str]) -> list[float]:
        return [0.96 if "operational intelligence" in value else 0.04 for value in documents]


def test_semantic_rerank_produces_high_confidence_for_supported_overview(monkeypatch):
    monkeypatch.setattr(graph_ranker, "get_semantic_provider", lambda: _SemanticProvider())
    monkeypatch.setattr(graph_ranker, "get_reranker", lambda: _Reranker())
    records = [
        {
            "id": "good",
            "text": "Runbook is an operational intelligence platform for cited company evidence.",
            "source_type": "repo_file",
            "source_title": "README.md",
            "source_url": "https://github.com/acme/runbook/blob/abc/README.md#L1-L8",
            "service_names": [],
            "metadata_json": "{}",
            "search_terms": [],
            "embedding": [1.0, 0.0],
            "embedding_model": "test-semantic",
        },
        {
            "id": "bad",
            "text": "Bananas grow in warm climates.",
            "source_type": "repo_file",
            "source_title": "fruit.md",
            "source_url": "",
            "service_names": [],
            "metadata_json": "{}",
            "search_terms": [],
            "embedding": [0.0, 1.0],
            "embedding_model": "test-semantic",
        },
    ]

    ranked = rank_records(records, "What is this repo about?", None, 4)

    assert ranked[0].chunk_id == "good"
    assert ranked[0].metadata["retrieval_confidence"] > 0.85
    assert ranked[0].metadata["reranker_model"] == "test-cross-encoder"


def test_structured_manifest_relevance_calibrates_low_prose_rerank(monkeypatch):
    monkeypatch.setattr(graph_ranker, "get_semantic_provider", lambda: _SemanticProvider())
    monkeypatch.setattr(graph_ranker, "get_reranker", lambda: _Reranker())
    records = [
        {
            "id": "manifest",
            "text": '{"dependencies":{"react":"19","vite":"6"},"scripts":{"dev":"vite"}}',
            "source_type": "repo_file",
            "source_title": "package.json",
            "source_url": "https://github.com/acme/app/blob/abc/package.json#L1-L8",
            "service_names": [],
            "metadata_json": "{}",
            "search_terms": [],
            "embedding": [1.0, 0.0],
            "embedding_model": "test-semantic",
        }
    ]

    ranked = rank_records(records, "What is the tech stack?", None, 4)

    assert ranked[0].metadata["rerank_score"] == 0.04
    assert ranked[0].metadata["structural_relevance"] == 1.0
    assert ranked[0].metadata["retrieval_confidence"] > 0.85


def test_retrieval_trace_uses_request_local_route(graph):
    adapter = HCAGAdapter(graph)
    project_id = IngestionService(graph, adapter, AuditService()).create_project("Trace isolation")
    first = adapter.route_query(project_id, "What is this repo about?")
    adapter.route_query(project_id, "What is the tech stack?")

    trace = adapter.build_retrieval_trace(project_id, "ignored", [], route=first)

    assert trace.resolved_query == "What is this repo about?"


def test_runbook_invocation_prefix_is_never_treated_as_a_repository_name():
    projects = {
        "sap": {"name": "Sanket/SAP-AI-PRs", "repository": "https://github.com/Sanket/SAP-AI-PRs"},
        "runbook": {
            "name": "Sanket/runbook",
            "repository": "https://github.com/Sanket/runbook",
        },
    }

    assert RetrievalService._named_project_ids("@runbook What is this repo about?", projects) == []
    assert RetrievalService._named_project_ids("Compare SAP-AI-PRs with this repo", projects) == [
        "sap"
    ]
    assert not RetrievalService._should_expand_workspace(
        "Trace SAP_BASE_URL through /api/requisition/submit", "configuration_locator"
    )
    assert RetrievalService._should_expand_workspace(
        "Trace SAP_BASE_URL across repositories", "configuration_locator"
    )


def test_contextual_chunks_are_line_addressable_and_bounded():
    content = "\n".join(
        f"Line {index}: repository authentication middleware validates the signed session token."
        for index in range(1, 420)
    )

    chunks = chunk_document(content)

    assert len(chunks) > 3
    assert all(chunk.line_start <= chunk.line_end for chunk in chunks)
    assert all(300 <= chunk.token_count <= 800 for chunk in chunks[:-1])
    assert chunks[1].line_start < chunks[0].line_end


def test_secret_values_are_redacted_before_storage_embedding_and_audit(graph):
    ingestion = IngestionService(graph, HCAGAdapter(graph), AuditService())
    project_id = ingestion.create_project("Secret boundary")
    secret = "sk-abcdefghijklmnopqrstuvwxyz1234567890"

    ingestion.ingest_item(
        project_id,
        "repo_file",
        ".env.example",
        f"OPENAI_API_KEY={secret}\nPUBLIC_API_URL=https://example.test",
        source_url="https://github.com/acme/runbook/blob/abc/.env.example",
        source_id=f"file:{project_id}:.env.example",
    )

    stored = row(
        "SELECT content,metadata_json FROM knowledge_items WHERE project_id=?", (project_id,)
    )
    assert stored
    assert secret not in stored["content"]
    assert "OPENAI_API_KEY=<redacted>" in stored["content"]
    assert all(
        secret not in item.get("text", "")
        for item in graph.list_nodes(project_id, "KnowledgeChunk")
    )
    assert all(secret not in str(item) for item in rows("SELECT * FROM audit_events"))


def test_legacy_graph_knowledge_items_are_scrubbed(graph):
    adapter = HCAGAdapter(graph)
    ingestion = IngestionService(graph, adapter, AuditService())
    project_id = ingestion.create_project("Legacy secret boundary")
    secret = "github_pat_abcdefghijklmnopqrstuvwxyz1234567890"
    graph.upsert_knowledge_item(
        {
            "id": "legacy-item",
            "project_id": project_id,
            "source_type": "repo_file",
            "source_title": "docs/setup.md",
            "content": f"GITHUB_TOKEN={secret}",
            "metadata_json": "{}",
        }
    )

    result = sanitize_existing_index(graph, adapter)
    item = next(
        value
        for value in graph.list_nodes(project_id, "KnowledgeItem", 20)
        if value["id"] == "legacy-item"
    )

    assert result["graph_items_scrubbed"] == 1
    assert secret not in item["content"]
    assert "<redacted>" in item["content"]


def test_repository_refresh_is_incremental_for_unchanged_content(graph, tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "README.md").write_text("# Delta repository\n\nOperational evidence lives here.")
    subprocess.run(["git", "init", str(repository)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repository), "add", "README.md"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Runbook Test",
            "-c",
            "user.email=test@runbook.local",
            "commit",
            "-m",
            "Initial evidence",
        ],
        check=True,
        capture_output=True,
    )
    ingestor = RepositoryIngestor(
        IngestionService(graph, HCAGAdapter(graph), AuditService()), graph
    )

    first = ingestor.ingest(str(repository), "Delta repository")
    second = ingestor.ingest(str(repository), "Delta repository")

    assert first["knowledge_items_created"] == 1
    assert second["knowledge_items_created"] == 0
    assert second["incremental"]["sources_unchanged"] == 1
    assert second["incremental"]["full_rebuild"] is False


def test_slack_refresh_deduplicates_legacy_items_and_then_becomes_incremental(graph):
    adapter = HCAGAdapter(graph)
    ingestion = IngestionService(graph, adapter, AuditService())
    project_id = ingestion.create_project("Slack delta")
    source_id = "slack-message:C123:1712345678.000100"
    metadata = {
        "channel_id": "C123",
        "channel_name": "operations",
        "timestamp": "1712345678.000100",
        "user": "U123",
    }
    for _ in range(2):
        ingestion.ingest_item(
            project_id,
            "slack",
            "#operations at 1712345678.000100",
            "The deployment window starts at 18:00 UTC.",
            "https://example.slack.com/archives/C123/p1712345678000100",
            source_id,
            metadata,
        )

    class SlackSource:
        def history(self, channel_id: str, limit: int):
            return {"id": channel_id, "name": "operations"}, [
                {
                    "ts": "1712345678.000100",
                    "text": "The deployment window starts at 18:00 UTC.",
                    "user": "U123",
                }
            ]

        def permalink(self, channel_id: str, ts: str) -> str:
            return f"https://example.slack.com/archives/{channel_id}/p{ts.replace('.', '')}"

    slack = SlackIngestor(ingestion, graph, SlackSource())
    repaired = slack.ingest_channel(project_id, "C123")
    unchanged = slack.ingest_channel(project_id, "C123")

    stored = row(
        "SELECT COUNT(*) count FROM knowledge_items WHERE project_id=? AND source_id=?",
        (project_id, source_id),
    )
    assert stored and stored["count"] == 1
    assert repaired["knowledge_items_created"] == 1
    assert unchanged["knowledge_items_created"] == 0
    assert unchanged["knowledge_chunks_created"] == 0
    assert unchanged["sources_unchanged"] == 1


def test_assertion_owner_suggestion_and_bulk_review(graph):
    ingestion = IngestionService(graph, HCAGAdapter(graph), AuditService())
    project_id = ingestion.create_project("Owned evidence")
    source = ingestion.ingest_item(
        project_id,
        "repo_file",
        "auth/session.py",
        "def validate_session(token): return token is not None",
        source_id=f"file:{project_id}:auth/session.py",
        metadata={"owner": "platform-auth", "owner_source": "CODEOWNERS"},
    )
    service = OperationalAssertionService(graph, AuditService())
    assertion = service.create(
        project_id,
        {
            "title": "Session validation",
            "claim": "Signed sessions are validated before access.",
            "verification_owner": "owner unknown",
            "evidence": [{"source_item_id": source["item_id"]}],
        },
    )

    suggested = service.assign_suggested_owners(project_id)
    updated = service.get(assertion["id"], project_id)

    assert suggested["updated"] == 1
    assert updated and updated["verification_owner"] == "platform-auth"
    reviewed = service.bulk_review(
        project_id,
        [assertion["id"]],
        "verify",
        "Test reviewer",
        "Evidence reviewed in bulk.",
    )
    assert reviewed["reviewed"] == 1
    assert reviewed["assertions"][0]["status"] == "verified"
