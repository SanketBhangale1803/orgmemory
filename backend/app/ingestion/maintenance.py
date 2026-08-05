from __future__ import annotations

import json
from typing import Any

from app.core.database import connect, row, rows, utcnow
from app.graph.base import GraphStore
from app.hcag_adapter import HCAGAdapter
from app.memory.company import CompanyMemoryService

from .extractors import extract_services
from .safety import sanitize_for_index, sanitize_metadata


def _sanitize_json_text(value: str) -> str:
    try:
        payload: Any = json.loads(value or "{}")
    except json.JSONDecodeError:
        return sanitize_for_index(value)[0]
    return json.dumps(sanitize_metadata(payload))


def sanitize_existing_index(graph: GraphStore, hcag: HCAGAdapter) -> dict[str, int]:
    """Idempotently scrub legacy evidence before it can be retrieved again."""
    items = graph_items = chunks = records = 0
    with connect() as conn:
        for item in rows("SELECT id,content,metadata_json FROM knowledge_items"):
            content, redactions = sanitize_for_index(item["content"])
            metadata = _sanitize_json_text(item["metadata_json"])
            if redactions or metadata != item["metadata_json"]:
                conn.execute(
                    "UPDATE knowledge_items SET content=?, metadata_json=? WHERE id=?",
                    (content, metadata, item["id"]),
                )
                items += 1
        for table, id_column, text_columns in (
            ("runbooks", "id", ("payload_json",)),
            ("operational_assertions", "id", ("evidence_json",)),
            ("audit_events", "id", ("summary", "payload_json")),
        ):
            for record in rows(f"SELECT {id_column},{','.join(text_columns)} FROM {table}"):
                updates = {
                    column: (
                        _sanitize_json_text(record[column])
                        if column.endswith("_json")
                        else sanitize_for_index(record[column] or "")[0]
                    )
                    for column in text_columns
                }
                if any(updates[column] != (record[column] or "") for column in text_columns):
                    assignments = ",".join(f"{column}=?" for column in text_columns)
                    conn.execute(
                        f"UPDATE {table} SET {assignments} WHERE {id_column}=?",
                        (*[updates[column] for column in text_columns], record[id_column]),
                    )
                    records += 1
    for project in rows("SELECT id FROM projects"):
        for item in graph.list_nodes(project["id"], "KnowledgeItem", 100_000):
            content, redactions = sanitize_for_index(str(item.get("content") or ""))
            metadata_raw = item.get("metadata_json") or "{}"
            metadata = _sanitize_json_text(metadata_raw)
            if redactions or metadata != metadata_raw:
                graph.upsert_knowledge_item(
                    {
                        "id": item["id"],
                        "project_id": project["id"],
                        "content": content,
                        "metadata_json": metadata,
                    }
                )
                graph_items += 1
        for chunk in graph.list_nodes(project["id"], "KnowledgeChunk", 100_000):
            text, redactions = sanitize_for_index(str(chunk.get("text") or ""))
            metadata_raw = chunk.get("metadata_json") or "{}"
            metadata = _sanitize_json_text(metadata_raw)
            if not redactions and metadata == metadata_raw:
                continue
            features = hcag.index_chunk(f"{chunk.get('source_title', '')}\n{text}")
            graph.upsert_chunk(
                {
                    "id": chunk["id"],
                    "project_id": project["id"],
                    "text": text,
                    "metadata_json": metadata,
                    "content_hash": features["content_hash"],
                    "search_terms": features["search_terms"],
                    "embedding": features.get("embedding", []),
                    "embedding_model": features.get("embedding_model", ""),
                    "embedding_version": features.get("embedding_version", 0),
                }
            )
            chunks += 1
    return {
        "items_scrubbed": items,
        "graph_items_scrubbed": graph_items,
        "chunks_scrubbed": chunks,
        "records_scrubbed": records,
    }


def reset_project_derived_memory(
    graph: GraphStore,
    project_id: str,
    *,
    repository_only: bool = False,
    clear_work_history: bool = True,
) -> dict[str, int]:
    """Remove derived/demo state while retaining authoritative source evidence.

    The next repository ingestion is forced through the current extraction
    schema. This is intentionally project-scoped and never removes another
    project's sources or memories.
    """

    project = row("SELECT id FROM projects WHERE id=?", (project_id,))
    if not project:
        raise ValueError("Project not found")

    removed_sources = 0
    retained_sources = 0
    removed_source_ids: list[str] = []
    repository_types = {
        "github_commit",
        "github_issue",
        "pull_request",
        "repo_file",
        "repository_metadata",
    }
    for item in rows(
        "SELECT id,source_id,source_type FROM knowledge_items WHERE project_id=?",
        (project_id,),
    ):
        if repository_only and item["source_type"] not in repository_types:
            graph.delete_source_knowledge(project_id, item["source_id"], item["source_type"])
            with connect() as conn:
                conn.execute("DELETE FROM knowledge_items WHERE id=?", (item["id"],))
                conn.execute(
                    "DELETE FROM source_scopes WHERE project_id=? AND source_id=?",
                    (project_id, item["source_id"]),
                )
            removed_source_ids.append(item["source_id"])
            removed_sources += 1
        else:
            retained_sources += 1

    # Remove every derived object that can retain a stale memory id. Raw
    # repository/document/Slack evidence remains unless repository_only=True.
    with connect() as conn:
        if clear_work_history:
            conn.execute("DELETE FROM memory_work WHERE project_id=?", (project_id,))
        conn.execute(
            """DELETE FROM artifact_impacts WHERE artifact_id IN
            (SELECT id FROM artifacts WHERE project_id=?)""",
            (project_id,),
        )
        for table in (
            "artifacts",
            "skill_specs",
            "context_envelopes",
            "memory_change_sets",
            "memory_relationships",
            "memory_units",
            "beliefs",
            "semantic_change_events",
            "operational_memories",
            "operational_assertions",
            "change_impacts",
            "runbooks",
            "actions",
        ):
            conn.execute(f"DELETE FROM {table} WHERE project_id=?", (project_id,))
        conn.execute("DELETE FROM memory_dynamics WHERE project_id=?", (project_id,))
        conn.execute("DELETE FROM project_context_states WHERE project_id=?", (project_id,))
        for source_id in removed_source_ids:
            conn.execute(
                "DELETE FROM source_revisions WHERE project_id=? AND source_id=?",
                (project_id, source_id),
            )
        for item in rows(
            "SELECT id,metadata_json FROM knowledge_items WHERE project_id=?",
            (project_id,),
        ):
            metadata = json.loads(item.get("metadata_json") or "{}")
            metadata["index_schema_version"] = 0
            metadata["memory_repair_requested_at"] = utcnow()
            conn.execute(
                "UPDATE knowledge_items SET metadata_json=? WHERE id=?",
                (json.dumps(metadata), item["id"]),
            )

    removed_nodes = graph.delete_project_nodes(
        project_id,
        [
            "Service",
            "SlackChannel",
            "SlackMessage",
            "Issue",
            "PullRequest",
            "Runbook",
            "RunbookStep",
            "EvidenceSource",
            "OperationalAssertion",
            "ChangeImpact",
            "Action",
            "Log",
            "MemoryUnit",
            "Belief",
            "BeliefEvidence",
            "SemanticChangeEvent",
            "MemoryEntity",
            "MemoryProfile",
            "MemoryTimeline",
            "MemoryConflict",
            "MemoryUpdate",
            "Decision",
            "Policy",
            "Procedure",
            "Fact",
            "Preference",
            "Convention",
            "Incident",
            "MemoryChangeSet",
            "Source",
            "SourceRevision",
            "ContextEnvelope",
            "Artifact",
            "ArtifactRevision",
            "SkillSpec",
        ],
    )
    return {
        "removed_sources": removed_sources,
        "retained_sources": retained_sources,
        "removed_graph_nodes": removed_nodes,
    }


def rebuild_services_from_index(graph: GraphStore, project_id: str) -> int:
    """Rebuild service nodes from retained, project-scoped knowledge only."""

    graph.delete_project_nodes(project_id, ["Service"])
    services: set[str] = set()
    for item in rows(
        "SELECT source_id,source_url,content FROM knowledge_items WHERE project_id=?",
        (project_id,),
    ):
        for service in extract_services(item["content"], item["source_url"]):
            services.add(service)
    services = {
        service
        for service in services
        if service not in {"client_service", "instagram_service"}
        and not ("-" not in service and "_" not in service and service.endswith("client"))
        and not any(
            candidate != service
            and len(candidate) > len(service)
            and candidate.endswith(f"-{service}")
            for candidate in services
        )
    }
    for service in sorted(services):
        service_id = f"{project_id}:{service}"
        graph.upsert_service({"id": service_id, "project_id": project_id, "name": service})
        graph.link("PROJECT_HAS_SERVICE", "Project", project_id, "Service", service_id)
    return len(services)


def rebuild_atomic_memories_from_index(
    graph: GraphStore,
    project_id: str,
    *,
    source_types: set[str] | None = None,
) -> int:
    """Re-extract retained sources without inventing a new source revision."""

    service = CompanyMemoryService(graph)
    chunks_by_item: dict[str, list[str]] = {}
    for chunk in graph.list_nodes(project_id, "KnowledgeChunk", 100_000):
        item_id = str(chunk.get("item_id") or "")
        if item_id:
            chunks_by_item.setdefault(item_id, []).append(chunk["id"])
    created: set[str] = set()
    for item in rows("SELECT * FROM knowledge_items WHERE project_id=?", (project_id,)):
        if source_types is not None and item["source_type"] not in source_types:
            continue
        metadata = json.loads(item.get("metadata_json") or "{}")
        for memory in service.extract_memory_units(
            project_id,
            item["id"],
            item["source_id"],
            item["source_type"],
            item["source_title"],
            item["content"],
            metadata,
            chunks_by_item.get(item["id"], []),
        ):
            created.add(memory["id"])
    return len(created)
