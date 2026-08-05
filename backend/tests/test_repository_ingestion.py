import json

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
    (repository / "demo_data").mkdir()
    (repository / "demo_data" / "sample_incident.md").write_text(
        "instagram_service must use MinIO."
    )
    (repository / "backend" / "scripts").mkdir(parents=True)
    (repository / "backend" / "scripts" / "load_demo.py").write_text("load_demo('client_service')")
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


def test_jupyter_notebooks_index_cells_without_outputs_or_metadata(graph, tmp_path):
    repository = tmp_path / "micrograd"
    repository.mkdir()
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {"private-note": "do not index metadata"},
                "source": ["# Micrograd\n", "A tiny scalar-valued autograd engine."],
            },
            {
                "cell_type": "code",
                "metadata": {},
                "source": [
                    "class Value:\n",
                    "    def backward(self):\n",
                    "        return self.grad\n",
                ],
                "outputs": [
                    {
                        "output_type": "stream",
                        "text": ["secret-output-must-not-be-indexed"],
                    }
                ],
                "execution_count": 42,
            },
        ],
        "metadata": {
            "kernelspec": {"language": "python"},
            "private-notebook-metadata": "do not index this",
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    (repository / "micrograd.ipynb").write_text(json.dumps(notebook))
    hcag = HCAGAdapter(graph)
    service = IngestionService(graph, hcag, AuditService())

    result = RepositoryIngestor(service, graph, GitHubConnector()).ingest(
        str(repository), "Micrograd"
    )

    assert result["files_scanned"] == 1
    item = rows(
        "SELECT content FROM knowledge_items WHERE project_id=? AND source_type='repo_file'",
        (result["project_id"],),
    )[0]
    assert "A tiny scalar-valued autograd engine." in item["content"]
    assert "class Value" in item["content"]
    assert "secret-output-must-not-be-indexed" not in item["content"]
    assert "private-notebook-metadata" not in item["content"]
    assert "private-note" not in item["content"]
