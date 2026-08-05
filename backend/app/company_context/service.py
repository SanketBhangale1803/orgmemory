"""Inspectable company-context briefing assembled from real product state."""

from __future__ import annotations

from typing import Any

from app.core.database import row, rows
from app.graph.base import GraphStore
from app.hcag_adapter.context_store import ProjectContextStore


class CompanyContextService:
    def __init__(self, graph: GraphStore, context_store: ProjectContextStore):
        self.graph = graph
        self.context_store = context_store

    def briefing(self, project_id: str) -> dict[str, Any]:
        project = row("SELECT * FROM projects WHERE id=?", (project_id,))
        if not project:
            raise ValueError("Project not found")
        context = self.context_store.get(project_id)
        source_rows = rows(
            "SELECT source_type, COUNT(*) count, MAX(created_at) latest_at "
            "FROM knowledge_items WHERE project_id=? GROUP BY source_type ORDER BY count DESC",
            (project_id,),
        )
        knowledge_count = sum(int(item["count"]) for item in source_rows)
        runbook_count = self._count("runbooks", project_id)
        memory_counts = self._status_counts("operational_memories", project_id)
        assertion_counts = self._status_counts("operational_assertions", project_id)
        approved_memories = [
            {
                "id": item["id"],
                "statement": item["statement"],
                "memory_type": item["memory_type"],
                "confidence": item["confidence"],
                "last_verified": item["last_verified"],
            }
            for item in rows(
                "SELECT id,statement,memory_type,confidence,last_verified "
                "FROM operational_memories WHERE project_id=? AND status='approved' "
                "ORDER BY updated_at DESC LIMIT 6",
                (project_id,),
            )
        ]
        at_risk_assertions = [
            {
                "id": item["id"],
                "title": item["title"],
                "claim": item["claim"],
                "status": item["status"],
                "environment_scope": item["environment_scope"],
                "updated_at": item["updated_at"],
            }
            for item in rows(
                "SELECT id,title,claim,status,environment_scope,updated_at "
                "FROM operational_assertions WHERE project_id=? "
                "AND status IN ('proposed','possibly_stale','stale','contradicted') "
                "ORDER BY updated_at DESC LIMIT 6",
                (project_id,),
            )
        ]
        try:
            summary = self.graph.graph_summary(project_id)
            graph_health = self.graph.health()
        except Exception as exc:
            summary = {"services": [], "total_nodes": 0}
            graph_health = {"connected": False, "error": str(exc)}
        windows = (
            self.graph.list_nodes(project_id, "ContextWindow", 50)
            if graph_health.get("connected")
            else []
        )
        persisted_window_counts = {
            f"{item['domain']}.{item['subdomain']}": int(item["count"])
            for item in rows(
                "SELECT json_extract(metadata_json, '$.hcag.domain') domain, "
                "json_extract(metadata_json, '$.hcag.subdomain') subdomain, COUNT(*) count "
                "FROM knowledge_items WHERE project_id=? "
                "AND json_extract(metadata_json, '$.hcag.domain') IS NOT NULL "
                "GROUP BY domain,subdomain",
                (project_id,),
            )
        }
        for window in windows:
            window["item_count"] = persisted_window_counts.get(window.get("name", ""), 0)
        services = [item.get("name") for item in summary.get("services", []) if item.get("name")]
        checks = {
            "evidence_indexed": knowledge_count > 0,
            "graph_connected": bool(graph_health.get("connected")),
            "context_routed": bool(windows),
            "operational_memory_verified": bool(memory_counts.get("approved")),
            "runbook_extracted": runbook_count > 0,
            "assertions_verified": bool(assertion_counts.get("verified")),
        }
        coverage = round(100 * sum(checks.values()) / len(checks))
        latest_at = max((item.get("latest_at") or "" for item in source_rows), default="")
        return {
            "project": project,
            "continuity": {
                **context,
                "persisted": bool(context.get("updated_at")),
                "mode": "project_scoped_hcag",
            },
            "knowledge": {
                "items": knowledge_count,
                "sources": source_rows,
                "services": services,
                "service_count": len(services),
                "context_windows": windows,
                "context_window_count": len(windows),
                "graph_nodes": int(summary.get("total_nodes") or 0),
                "runbooks": runbook_count,
                "memory_status": memory_counts,
                "assertion_status": assertion_counts,
                "last_ingested_at": latest_at,
            },
            "commitments": approved_memories,
            "risks": at_risk_assertions,
            "coverage": {
                "score": coverage,
                "level": (
                    "established" if coverage >= 80 else "partial" if coverage >= 35 else "empty"
                ),
                "checks": checks,
                "meaning": "Coverage of connected, verified company context; not a model accuracy claim.",
            },
        }

    @staticmethod
    def _count(table: str, project_id: str) -> int:
        result = row(f"SELECT COUNT(*) value FROM {table} WHERE project_id=?", (project_id,))
        return int((result or {}).get("value") or 0)

    @staticmethod
    def _status_counts(table: str, project_id: str) -> dict[str, int]:
        return {
            item["status"]: int(item["count"])
            for item in rows(
                f"SELECT status, COUNT(*) count FROM {table} WHERE project_id=? GROUP BY status",
                (project_id,),
            )
        }
