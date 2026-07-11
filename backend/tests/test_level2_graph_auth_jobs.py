from app.audit import AuditService
from app.auth.app_auth import create_dev_session, create_workspace, invite_member, workspace_members
from app.connectors.github import GitHubConnector
from app.core.database import row
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.ingestion.repository import RepositoryIngestor


def test_repo_ingestion_builds_file_service_and_code_graph(graph, tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / "README.md").write_text("# Graph repo\nreddit_service handles Kafka messages.")
    (repository / "app.py").write_text(
        "import os\n"
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "KAFKA_URL = os.getenv('KAFKA_URL')\n"
        "@app.get('/health')\n"
        "def health():\n"
        "    return {'ok': True}\n"
    )
    (repository / "docker-compose.yml").write_text(
        "services:\n"
        "  reddit_service:\n"
        "    image: reddit:dev\n"
        "    depends_on:\n"
        "      - kafka\n"
        "    environment:\n"
        "      KAFKA_URL: kafka:9092\n"
        "  kafka:\n"
        "    image: bitnami/kafka\n"
    )
    (repository / "style.css").write_text(".button { width:30px; font-weight:600; }")

    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    result = RepositoryIngestor(ingestion, graph, GitHubConnector()).ingest(
        str(repository), "Graph repo"
    )

    summary = graph.graph_summary(result["project_id"])
    assert summary["node_counts"]["File"] == 4
    assert summary["node_counts"]["Service"] >= 2
    service_names = {service["name"] for service in summary["services"]}
    assert "width" not in service_names
    assert "font-weight" not in service_names
    assert summary["node_counts"]["Endpoint"] == 1
    assert summary["node_counts"]["EnvironmentVariable"] >= 1
    assert summary["edge_counts"]["FILE_DEFINES_ENDPOINT"] == 1
    assert graph.service_graph(result["project_id"], "reddit_service")["edges"]


def test_ingestion_job_helpers_record_progress(graph):
    from app.api.routes import _create_job, _finish_job

    job_id = _create_job("upload", "incident.md", project_id="prj_test")
    _finish_job(
        job_id,
        "succeeded",
        {
            "project_id": "prj_test",
            "knowledge_items_created": 1,
            "knowledge_chunks_created": 2,
            "graph_nodes_created": 3,
            "graph_edges_created": 4,
        },
    )

    job = row("SELECT * FROM ingestion_jobs WHERE id=?", (job_id,))
    assert job["status"] == "succeeded"
    assert job["progress"] == 100
    assert job["graph_nodes_created"] == 3


def test_dev_auth_workspace_and_invite_flow(graph):
    session = create_dev_session("owner@example.com", "Owner")
    assert session["token"].startswith("rb_")
    workspace = create_workspace("Pilot Workspace", session["token"])
    invited = invite_member(workspace["id"], "member@example.com", "member")

    assert invited["status"] == "invited"
    members = workspace_members(workspace["id"])
    assert {member["email"] for member in members} >= {"owner@example.com", "member@example.com"}
