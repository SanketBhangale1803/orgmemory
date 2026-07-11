from app.audit import AuditService
from app.connectors.github import GitHubConnector
from app.core.config import settings
from app.core.database import rows
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.ingestion.repository import RepositoryIngestor


def test_container_path_mapping_and_useful_file_scan(graph, tmp_path):
    mounted = tmp_path / "mounted"
    repository = mounted / "private-service"
    repository.mkdir(parents=True)
    (repository / "README.md").write_text("private_service failed because config is missing")
    (repository / "Jenkinsfile").write_text("pipeline { stages { stage('test') {} } }")
    (repository / "app.js").write_text("export function start() { return 'ready'; }")
    (repository / "cookies.txt").write_text("session=must-not-be-indexed")
    (repository / "package-lock.json").write_text('{"lockfileVersion": 3}')
    (repository / "binary.bin").write_bytes(b"\x00\x01")
    settings.local_repo_mount = mounted
    hcag = HCAGAdapter(graph)
    service = IngestionService(graph, hcag, AuditService())

    result = RepositoryIngestor(service, graph, GitHubConnector()).ingest(
        "/Users/example/Desktop/startup/private-service", "Private service"
    )

    assert result["files_scanned"] == 3
    assert result["knowledge_items_created"] == 3
    assert result["status"] == "success"
    project_id = result["project_id"]

    repeated = RepositoryIngestor(service, graph, GitHubConnector()).ingest(
        "/Users/example/Desktop/startup/private-service", "Private service"
    )
    assert repeated["project_id"] == project_id
    assert (
        len(
            rows(
                "SELECT id FROM projects WHERE repository=?",
                ("/Users/example/Desktop/startup/private-service",),
            )
        )
        == 1
    )
    assert len(rows("SELECT id FROM knowledge_items WHERE project_id=?", (project_id,))) == 3
    assert any(edge["relationship"] == "KNOWLEDGE_ITEM_DERIVED_FROM" for edge in graph.edges)
