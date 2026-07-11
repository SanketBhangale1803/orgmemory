from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from app.audit import AuditService
from app.core.database import row
from app.graph import get_graph_store
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.runbooks import RunbookService


def main() -> None:
    graph = get_graph_store()
    graph.initialize()
    hcag = HCAGAdapter(graph)
    audit = AuditService()
    ingestion = IngestionService(graph, hcag, audit)
    existing = row("SELECT id FROM projects WHERE name=?", ("Runbook Operations Demo",))
    project_id = (
        existing["id"]
        if existing
        else ingestion.create_project("Runbook Operations Demo", "demo://operations")
    )
    demo_dir = ROOT / "demo_data"
    source_types = {
        ".log": "log",
        ".yml": "doc",
        ".yaml": "doc",
    }
    for path in sorted(demo_dir.glob("sample_*")):
        already = row(
            "SELECT id FROM knowledge_items WHERE project_id=? AND source_title=?",
            (project_id, path.name),
        )
        if already:
            continue
        source_type = source_types.get(
            path.suffix,
            (
                "slack_export"
                if "slack" in path.name
                else (
                    "incident"
                    if "incident" in path.name
                    else "github_issue_export" if "github_issue" in path.name else "doc"
                )
            ),
        )
        ingestion.ingest_item(
            project_id,
            source_type,
            path.name,
            path.read_text(encoding="utf-8"),
            f"demo://{path.name}",
        )
    extractor = RunbookService(graph, hcag, audit)
    for query in (
        "Kafka connection timeout recovery procedure for reddit_service",
        "instagram_service downloaded media /tmp/media storage",
        "Jenkins integration-test KafkaTimeoutError build failure",
    ):
        extractor.extract(project_id, query)
    print(f"Demo loaded through the ingestion pipeline. project_id={project_id}")


if __name__ == "__main__":
    main()
