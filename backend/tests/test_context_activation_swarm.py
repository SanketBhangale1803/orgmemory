import json

from app.audit import AuditService
from app.auth.app_auth import create_dev_session
from app.core.database import connect, decode, row
from app.governance import ScopeService
from app.graph.base import GraphEvidence
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService
from app.swarm import ContextActivationSwarm


def test_graph_forager_reaches_chunk_through_bounded_relationships(graph):
    project_id = "project_swarm_graph"
    graph.upsert_project({"id": project_id, "project_id": project_id, "name": "Swarm"})
    graph.upsert_service(
        {
            "id": f"{project_id}:payments_service",
            "project_id": project_id,
            "name": "payments_service",
        }
    )
    graph.upsert_file(
        {
            "id": f"{project_id}:src/payments.py",
            "project_id": project_id,
            "path": "src/payments.py",
            "filename": "payments.py",
        }
    )
    graph.upsert_chunk(
        {
            "id": "chunk_payments",
            "project_id": project_id,
            "text": "Payments are retried through the durable settlement queue.",
            "source_type": "repo_file",
            "source_title": "src/payments.py",
            "source_url": "",
            "service_names": json.dumps(["payments_service"]),
            "metadata_json": json.dumps({"source_id": "source:payments"}),
        }
    )
    graph.link(
        "SERVICE_DEFINED_IN_FILE",
        "Service",
        f"{project_id}:payments_service",
        "File",
        f"{project_id}:src/payments.py",
    )
    graph.link(
        "FILE_HAS_CHUNK",
        "File",
        f"{project_id}:src/payments.py",
        "KnowledgeChunk",
        "chunk_payments",
    )

    evidence = graph.traverse_context(
        project_id, "How does payments_service settle requests?", max_hops=2
    )

    assert [item.chunk_id for item in evidence] == ["chunk_payments"]
    assert evidence[0].metadata["graph_hops"] == 2
    assert [edge["relationship"] for edge in evidence[0].metadata["graph_path_edges"]] == [
        "SERVICE_DEFINED_IN_FILE",
        "FILE_HAS_CHUNK",
    ]


def test_ask_runs_specialists_and_persists_compiled_context(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Swarm context")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        "Swarm context is a Python service that indexes durable organizational knowledge.",
        source_id="readme:swarm",
    )

    result = RetrievalService(hcag).ask(
        project_id,
        "What is this repository about?",
        principal={"id": "agent-reader"},
        token_budget=500,
    )

    swarm = result["retrieval_trace"]["plan"]["context_activation_swarm"]
    assert swarm["active_run_id"]
    assert {report["agent"] for report in swarm["runs"][0]["agents"]} == {
        "sensory_activation",
        "graph_forager",
        "current_truth_historian",
    }
    assert swarm["compiled_context"]["token_count"] <= 400
    assert result["context_envelope"]["activation_run_ids"] == [swarm["active_run_id"]]
    assert "README.md" in result["context_envelope"]["compiled_context"]["content"]
    assert result["context_envelope"]["source_version_vector"] == {"readme:swarm": 1}

    stored = decode(
        row(
            "SELECT * FROM context_activation_runs WHERE id=?",
            (swarm["active_run_id"],),
        )
        or {}
    )
    assert stored["status"] == "complete"
    assert stored["principal_id"] == "agent-reader"
    assert stored["compiled_context"]["token_count"] <= 400


def test_swarm_degrades_when_one_specialist_fails(graph, monkeypatch):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Resilient swarm")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "README.md",
        (
            "Resilient swarm is a customer notification service. "
            "It sends transactional email and delivery-status webhooks."
        ),
        source_id="doc:overview",
    )

    def fail_traversal(*args, **kwargs):
        raise RuntimeError("graph temporarily unavailable")

    monkeypatch.setattr(graph, "traverse_context", fail_traversal)
    result = RetrievalService(hcag).ask(project_id, "What is this repository about?")
    run = result["retrieval_trace"]["plan"]["context_activation_swarm"]["runs"][0]

    assert result["evidence"]
    assert run["status"] == "degraded"
    assert run["failed_agents"] == ["graph_forager"]
    assert next(report for report in run["agents"] if report["agent"] == "graph_forager")[
        "error"
    ].startswith("RuntimeError:")


def test_context_compiler_never_exceeds_its_evidence_budget(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Bounded swarm")
    swarm = ContextActivationSwarm(hcag)
    candidates = [
        GraphEvidence(
            chunk_id=f"chunk_{index}",
            text=("long source-backed evidence " * 100),
            source_type="doc",
            source_title=f"Source {index}",
            source_url="",
            metadata={"source_id": f"source:{index}"},
            score=20 - index,
        )
        for index in range(4)
    ]
    report = swarm.specialist_report(
        "test_forager",
        "test evidence",
        project_id,
        candidates,
        allowed_team_ids=None,
    )

    activation = swarm.compile(
        project_id,
        "bounded context",
        [report],
        principal_id="test",
        token_budget=100,
    )

    assert activation.compiled_context["evidence_token_budget"] == 80
    assert activation.compiled_context["token_count"] <= 80
    assert activation.evidence[0].metadata["context_truncated"] is True


def test_specialists_cannot_compile_evidence_outside_team_scope(graph):
    session = create_dev_session("swarm-owner@company.test", "Swarm Owner")
    workspace_id = session["user"]["active_workspace_id"]
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Scoped swarm")
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO workspace_projects VALUES (?,?)",
            (workspace_id, project_id),
        )
    scopes = ScopeService()
    platform = scopes.create_team(workspace_id, "Platform")
    finance = scopes.create_team(workspace_id, "Finance")
    ingestion.ingest_item(
        project_id,
        "doc",
        "Private launch plan",
        "The secret launch codename is winter-orchid.",
        source_id="private:launch",
        metadata={"team_ids": [platform["id"]]},
    )

    result = RetrievalService(hcag).ask(
        project_id,
        "What is the secret launch codename?",
        principal={"id": "finance-agent"},
        allowed_team_ids=[finance["id"]],
    )
    run_id = result["context_envelope"]["activation_run_ids"][-1]
    stored = decode(row("SELECT * FROM context_activation_runs WHERE id=?", (run_id,)) or {})

    assert result["evidence"] == []
    assert "winter-orchid" not in stored["compiled_context"]["content"]
    assert stored["selected_evidence_ids"] == []
