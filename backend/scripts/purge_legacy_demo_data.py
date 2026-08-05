from __future__ import annotations

from app.core.database import connect, rows
from app.graph import get_graph_store
from app.ingestion.maintenance import (
    rebuild_atomic_memories_from_index,
    rebuild_services_from_index,
    reset_project_derived_memory,
)

DEMO_PROJECT_NAMES = {"Runbook Operations Demo"}
DEMO_SOURCE_TITLES = {
    "backend/scripts/load_demo.py",
    "demo_data/sample_docker_compose.yml",
    "demo_data/sample_github_issue_instagram_media.md",
    "sample_docker_compose.yml",
    "sample_github_issue_instagram_media.md",
}
LEGACY_TABLES_WITHOUT_PROJECT_CASCADE = {
    "actions",
    "audit_events",
    "change_impacts",
    "ingestion_jobs",
    "operational_assertions",
    "operational_memories",
}


def purge() -> dict[str, int]:
    """Remove the retired product demo without touching real connected sources."""

    graph = get_graph_store()
    removed_projects = removed_sources = removed_work = rebuilt_projects = 0

    for project in rows("SELECT id,name FROM projects ORDER BY id"):
        if project["name"] not in DEMO_PROJECT_NAMES:
            continue
        graph.delete_project(project["id"])
        with connect() as conn:
            for table in LEGACY_TABLES_WITHOUT_PROJECT_CASCADE:
                conn.execute(f"DELETE FROM {table} WHERE project_id=?", (project["id"],))
            conn.execute("DELETE FROM projects WHERE id=?", (project["id"],))
        removed_projects += 1

    affected_projects: set[str] = set()
    for item in rows(
        """SELECT id,project_id,source_id,source_type,source_title,content
        FROM knowledge_items ORDER BY project_id,id"""
    ):
        title = str(item["source_title"] or "").casefold()
        content = str(item["content"] or "").casefold()
        retired_demo_source = (
            title.startswith("demo_data/")
            or title in DEMO_SOURCE_TITLES
            or (
                item["source_type"] != "repo_file"
                and "minio" in content
                and any(
                    marker in content
                    for marker in (
                        "instagram_service",
                        "local filesystem",
                        "production media",
                    )
                )
            )
        )
        if not retired_demo_source:
            continue
        graph.delete_source_knowledge(item["project_id"], item["source_id"], item["source_type"])
        with connect() as conn:
            conn.execute("DELETE FROM knowledge_items WHERE id=?", (item["id"],))
            conn.execute(
                "DELETE FROM source_scopes WHERE project_id=? AND source_id=?",
                (item["project_id"], item["source_id"]),
            )
            conn.execute(
                "DELETE FROM memory_change_sets WHERE project_id=? AND source_id=?",
                (item["project_id"], item["source_id"]),
            )
            conn.execute(
                "DELETE FROM source_revisions WHERE project_id=? AND source_id=?",
                (item["project_id"], item["source_id"]),
            )
        affected_projects.add(item["project_id"])
        removed_sources += 1

    for project_id in sorted(affected_projects):
        reset_project_derived_memory(
            graph,
            project_id,
            repository_only=False,
            clear_work_history=True,
        )
        rebuild_atomic_memories_from_index(graph, project_id)
        rebuild_services_from_index(graph, project_id)
        rebuilt_projects += 1

    for project in rows("SELECT id FROM projects ORDER BY id"):
        rebuild_services_from_index(graph, project["id"])

    with connect() as conn:
        removed_work = int((conn.execute("SELECT count(*) FROM memory_work").fetchone() or [0])[0])
        conn.execute("DELETE FROM memory_work")

    return {
        "removed_projects": removed_projects,
        "removed_sources": removed_sources,
        "removed_work": removed_work,
        "rebuilt_projects": rebuilt_projects,
    }


if __name__ == "__main__":
    print(purge())
