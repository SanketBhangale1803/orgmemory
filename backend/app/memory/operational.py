"""Company-specific operational memory.

Operational memories are structured statements about how a company operates
("Kafka incidents escalate to the platform team", "production restarts
require approval"). They are only ever created from ingested evidence, and
they stay in `proposed` status until a human approves them. Approved
memories are written to the graph with OPERATIONAL_MEMORY_BACKED_BY edges to
their supporting knowledge items so provenance is queryable.

Nothing here stores unverified assumptions: every candidate carries the
exact source line it was derived from.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.audit import AuditService
from app.core.database import connect, new_id, row, rows, utcnow
from app.graph.base import GraphStore

# Patterns that indicate a durable operational rule rather than a one-off
# remark. Each match becomes a candidate memory citing its source line.
RULE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "approval_policy",
        re.compile(
            r"(?im)^(?:.*\b(?:requires?|needs?|must have)\s+(?:\w+\s+)?approval\b.*"
            r"|.*\bapproved? by\s+[A-Za-z].*)$"
        ),
    ),
    (
        "escalation",
        re.compile(r"(?im)^.*\bescalat\w+\s+(?:to|via)\s+.*$"),
    ),
    (
        "channel_convention",
        re.compile(r"(?im)^.*#[a-z0-9][\w-]{2,}.*(?:incident|outage|alert|failure|production).*$"),
    ),
    (
        "storage_convention",
        re.compile(r"(?im)^.*\b(?:stored?|saves?|writes?)\s+(?:under|in|to)\s+/[\w{}./-]+.*$"),
    ),
    (
        "ownership",
        re.compile(r"(?im)^(?:.*\bowner:\s*[A-Za-z].*|.*\bowned by\s+[A-Za-z].*)$"),
    ),
]
MAX_LINE = 300


class OperationalMemoryService:
    def __init__(self, graph: GraphStore, audit: AuditService | None = None):
        self.graph = graph
        self.audit = audit or AuditService()

    def derive(self, project_id: str) -> dict[str, Any]:
        """Scan ingested evidence for operational rules; store new candidates."""
        items = rows(
            "SELECT id, source_type, source_title, source_url, content FROM knowledge_items "
            "WHERE project_id=? ORDER BY created_at DESC LIMIT 300",
            (project_id,),
        )
        existing = {
            record["statement"]
            for record in rows(
                "SELECT statement FROM operational_memories WHERE project_id=?", (project_id,)
            )
        }
        created: list[dict[str, Any]] = []
        for item in items:
            for memory_type, pattern in RULE_PATTERNS:
                for match in pattern.finditer(item["content"]):
                    statement = " ".join(match.group(0).split()).strip(" -*#>")[:MAX_LINE]
                    if len(statement) < 16 or statement in existing:
                        continue
                    existing.add(statement)
                    created.append(self._store_candidate(project_id, memory_type, statement, item))
        if created:
            self.audit.record(
                "memory.derived",
                f"Derived {len(created)} operational memory candidate(s)",
                project_id,
                payload={"memory_ids": [memory["id"] for memory in created]},
            )
        return {"project_id": project_id, "candidates_created": len(created), "memories": created}

    def _store_candidate(
        self, project_id: str, memory_type: str, statement: str, item: dict[str, Any]
    ) -> dict[str, Any]:
        memory_id = new_id("mem")
        now = utcnow()
        evidence = [
            {
                "item_id": item["id"],
                "source_type": item["source_type"],
                "source_title": item["source_title"],
                "source_url": item["source_url"],
                "snippet": statement,
            }
        ]
        with connect() as conn:
            conn.execute(
                "INSERT INTO operational_memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    memory_id,
                    project_id,
                    statement,
                    memory_type,
                    "project",
                    "",
                    "",
                    0.5,  # single-source candidate; approval raises trust, not confidence
                    "proposed",
                    json.dumps([item["id"]]),
                    json.dumps(evidence),
                    now,
                    "",
                    now,
                    now,
                ),
            )
        return self.get(memory_id)

    def get(self, memory_id: str) -> dict[str, Any]:
        record = row("SELECT * FROM operational_memories WHERE id=?", (memory_id,))
        if not record:
            raise ValueError("Operational memory not found")
        record["source_item_ids"] = json.loads(record.pop("source_item_ids_json"))
        record["evidence"] = json.loads(record.pop("evidence_json"))
        return record

    def list(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            records = rows(
                "SELECT id FROM operational_memories WHERE project_id=? AND status=? "
                "ORDER BY created_at DESC",
                (project_id, status),
            )
        else:
            records = rows(
                "SELECT id FROM operational_memories WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            )
        return [self.get(record["id"]) for record in records]

    def resolve(self, memory_id: str, approved: bool, resolved_by: str) -> dict[str, Any]:
        memory = self.get(memory_id)
        if memory["status"] != "proposed":
            raise ValueError("Memory is not awaiting review")
        status = "approved" if approved else "rejected"
        now = utcnow()
        with connect() as conn:
            conn.execute(
                "UPDATE operational_memories SET status=?, approved_by=?, last_verified=?, "
                "updated_at=? WHERE id=?",
                (status, resolved_by, now, now, memory_id),
            )
        if approved:
            try:
                self.graph.upsert_node(
                    "OperationalMemory",
                    {
                        "id": memory_id,
                        "project_id": memory["project_id"],
                        "statement": memory["statement"],
                        "memory_type": memory["memory_type"],
                        "scope": memory["scope"],
                        "approved_by": resolved_by,
                        "last_verified": now,
                    },
                )
                for item_id in memory["source_item_ids"]:
                    self.graph.link(
                        "OPERATIONAL_MEMORY_BACKED_BY",
                        "OperationalMemory",
                        memory_id,
                        "KnowledgeItem",
                        item_id,
                    )
            except Exception:
                pass  # graph unavailability must not lose the approval record
        self.audit.record(
            f"memory.{status}",
            f"Operational memory {status} by {resolved_by}",
            memory["project_id"],
            resolved_by,
            {"memory_id": memory_id, "statement": memory["statement"]},
        )
        return self.get(memory_id)
