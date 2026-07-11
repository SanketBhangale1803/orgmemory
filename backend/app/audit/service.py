from __future__ import annotations

import json
from typing import Any

from app.core.database import connect, new_id, rows, utcnow


class AuditService:
    def record(
        self,
        event_type: str,
        summary: str,
        project_id: str | None = None,
        actor: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> str:
        event_id = new_id("audit")
        with connect() as conn:
            conn.execute(
                "INSERT INTO audit_events VALUES (?,?,?,?,?,?,?)",
                (
                    event_id,
                    project_id,
                    event_type,
                    actor,
                    summary,
                    json.dumps(payload or {}),
                    utcnow(),
                ),
            )
        return event_id

    def list(self, project_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        if project_id:
            records = rows(
                "SELECT * FROM audit_events WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
                (project_id, limit),
            )
        else:
            records = rows("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,))
        for record in records:
            record["payload"] = json.loads(record.pop("payload_json"))
        return records
