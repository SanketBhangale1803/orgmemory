"""Persist HCAG context windows in Runbook's graph store.

Every routed ingestion updates a per-project `ContextWindow` vertex with
its domain/subdomain and a running item count, so the Repo Graph page can
show which context windows exist and how much knowledge each holds. This
uses the same `GraphStore` interface as the rest of the product (ArcadeDB
in production, in-memory in tests).
"""

from __future__ import annotations

from typing import Any

from app.core.database import utcnow
from app.graph.base import GraphStore


def canonical_window_id(project_id: str, domain: str, subdomain: str) -> str:
    return f"win:{project_id}:{domain}.{subdomain}".replace(" ", "_").lower()


class ArcadeDBWindowStore:
    def __init__(self, graph: GraphStore):
        self.graph = graph
        self._counts: dict[str, int] = {}

    def ensure_window(self, project_id: str, domain: str, subdomain: str) -> str:
        window_id = canonical_window_id(project_id, domain, subdomain)
        self._counts[window_id] = self._counts.get(window_id, 0)
        self.graph.upsert_node(
            "ContextWindow",
            {
                "id": window_id,
                "project_id": project_id,
                "domain": domain,
                "subdomain": subdomain,
                "name": f"{domain}.{subdomain}",
                "item_count": self._counts[window_id],
                "updated_at": utcnow(),
            },
        )
        return window_id

    def record_item(self, project_id: str, domain: str, subdomain: str) -> str:
        window_id = self.ensure_window(project_id, domain, subdomain)
        self._counts[window_id] += 1
        self.graph.upsert_node(
            "ContextWindow",
            {
                "id": window_id,
                "project_id": project_id,
                "domain": domain,
                "subdomain": subdomain,
                "name": f"{domain}.{subdomain}",
                "item_count": self._counts[window_id],
                "updated_at": utcnow(),
            },
        )
        return window_id

    def list_windows(self, project_id: str) -> list[dict[str, Any]]:
        return self.graph.list_nodes(project_id, "ContextWindow", 200)
