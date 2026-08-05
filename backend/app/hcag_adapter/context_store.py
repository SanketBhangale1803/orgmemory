"""Durable, project-scoped context continuity for HCAG routing.

The context state is intentionally small and inspectable. It remembers the
active operational domain and service across API processes/restarts, while the
answer itself is still regenerated from current cited evidence on every query.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.database import connect, row, utcnow

FOLLOW_UP_PATTERN = re.compile(
    r"\b(?:it|its|this|that|same|there|again|what about|and then)\b",
    re.IGNORECASE,
)


class ProjectContextStore:
    def get(self, project_id: str) -> dict[str, Any]:
        state = row("SELECT * FROM project_context_states WHERE project_id=?", (project_id,))
        return state or {
            "project_id": project_id,
            "active_domain": "",
            "active_subdomain": "",
            "context_window": "",
            "active_service": "",
            "boundary_type": "none",
            "query_type": "single_hop",
            "query_count": 0,
            "last_query": "",
            "resolved_query": "",
            "created_at": "",
            "updated_at": "",
        }

    @staticmethod
    def should_reuse_service(query: str) -> bool:
        # Short questions are not automatically follow-ups. "Who approves
        # production restarts?" is short but self-contained; carrying a prior
        # service into it silently contaminates retrieval. Reuse requires an
        # explicit referential cue such as "it", "same", or "what about".
        return bool(FOLLOW_UP_PATTERN.search(query))

    def resolve_service(
        self, project_id: str, query: str, detected_service: str | None
    ) -> tuple[str | None, bool]:
        if detected_service:
            return detected_service, False
        previous = self.get(project_id).get("active_service") or ""
        if previous and self.should_reuse_service(query):
            return previous, True
        return None, False

    @staticmethod
    def enrich_query(query: str, service_name: str | None, reused: bool) -> str:
        if not (service_name and reused):
            return query
        return f"{query.rstrip()} [active service: {service_name}]"

    def record(
        self,
        project_id: str,
        *,
        domain: str,
        subdomain: str,
        context_window: str,
        service_name: str | None,
        boundary_type: str,
        query_type: str,
        query: str,
        resolved_query: str,
    ) -> dict[str, Any]:
        previous = self.get(project_id)
        now = utcnow()
        created_at = previous.get("created_at") or now
        query_count = int(previous.get("query_count") or 0) + 1
        with connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO project_context_states VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    project_id,
                    domain,
                    subdomain,
                    context_window,
                    # `service_name` already contains the previous service when
                    # this turn was classified as a real follow-up. Otherwise
                    # clear it so unrelated questions cannot inherit stale scope.
                    service_name or "",
                    boundary_type,
                    query_type,
                    query_count,
                    query,
                    resolved_query,
                    created_at,
                    now,
                ),
            )
        return self.get(project_id)
