from __future__ import annotations

import contextlib
import re
import sys
from typing import Any

from app.core.config import settings
from app.graph.base import GraphEvidence, GraphStore

from .arcadedb_window_store import ArcadeDBWindowStore
from .fallback import FallbackPlanner
from .models import HCAGTrace, RouteResult


class HCAGAdapter:
    def __init__(self, graph: GraphStore):
        self.graph = graph
        self.planner: Any = FallbackPlanner()
        self.engine = "hcag_fallback_planner"
        self.window_store = ArcadeDBWindowStore(graph)
        self._last_route: dict[str, RouteResult] = {}
        try:
            source_path = str(settings.hcag_path)
            if source_path not in sys.path:
                sys.path.insert(0, source_path)
            from query_planner import QueryPlanner

            self.planner = QueryPlanner()
            self.engine = "hcag_query_planner_arcadedb"
        except Exception:
            pass

    def ingest_knowledge_item(self, item: dict[str, Any]) -> dict[str, Any]:
        route = self.route_query(
            item["project_id"], f"{item['source_title']}\n{item['content'][:1200]}"
        )
        # Window bookkeeping must not block ingestion.
        with contextlib.suppress(Exception):
            self.window_store.record_item(item["project_id"], route.domain, route.subdomain)
        return {
            "domain": route.domain,
            "subdomain": route.subdomain,
            "context_window": route.context_window,
        }

    def route_query(self, project_id: str, query: str) -> RouteResult:
        cleaned = re.sub(r"^\s*@runbook\b", "", query, flags=re.IGNORECASE).strip()
        service_match = re.search(r"\b([a-zA-Z][\w-]*(?:_service|-service))\b", cleaned)
        service_name = service_match.group(1).lower() if service_match else None
        lowered = cleaned.lower()
        if any(term in lowered for term in ("pipeline", "jenkins", "build", "deploy", "workflow")):
            subdomain = "ci_cd"
        elif any(
            term in lowered
            for term in ("fail", "error", "timeout", "incident", "outage", "root cause")
        ):
            subdomain = "incident_response"
        elif any(term in lowered for term in ("storage", "media", "volume", "backup")):
            subdomain = "service_operations"
        else:
            subdomain = "engineering_knowledge"
        query_type = self.planner.classify(cleaned)
        previous = self._last_route.get(project_id)
        boundary = self.detect_boundary(previous.context_window if previous else "", subdomain)
        context_window = f"engineering_operations.{subdomain}"
        route = RouteResult(
            domain="engineering_operations",
            subdomain=subdomain,
            context_window=context_window,
            query_type=query_type,
            service_name=service_name,
            boundary_type=boundary,
            confidence=0.9 if service_name else 0.78,
        )
        self._last_route[project_id] = route
        return route

    def retrieve_context(
        self, project_id: str, query: str, service_name: str | None = None
    ) -> list[GraphEvidence]:
        route = self.route_query(project_id, query)
        return self.graph.retrieve_context(project_id, query, service_name or route.service_name)

    def detect_boundary(self, previous_query: str, current_query: str) -> str:
        if not previous_query:
            return "none"
        previous = previous_query.rsplit(".", 1)[-1]
        current = current_query.rsplit(".", 1)[-1]
        if previous == current:
            return "none"
        operational = {"incident_response", "ci_cd", "service_operations"}
        return "soft" if previous in operational and current in operational else "hard"

    def build_retrieval_trace(
        self, project_id: str, query: str, evidence: list[GraphEvidence]
    ) -> HCAGTrace:
        route = self._last_route.get(project_id) or self.route_query(project_id, query)
        graph_paths = self.graph.get_retrieval_trace(
            project_id, [item.chunk_id for item in evidence]
        )
        confidences = [float(item.metadata.get("retrieval_confidence", 0.0)) for item in evidence]
        return HCAGTrace(
            domain=route.domain,
            subdomain=route.subdomain,
            context_window=route.context_window,
            boundary_type=route.boundary_type,
            query_type=route.query_type,
            retrieved_chunk_ids=[item.chunk_id for item in evidence],
            graph_paths=graph_paths,
            confidence=round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
            engine=self.engine,
        )
