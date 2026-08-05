from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
from typing import Any

from app.core.config import settings
from app.graph.base import GraphEvidence, GraphStore
from app.retrieval.semantic import get_semantic_provider
from app.retrieval.universal import plan_query

from .arcadedb_window_store import ArcadeDBWindowStore
from .context_store import ProjectContextStore
from .fallback import FallbackPlanner
from .models import HCAGTrace, RouteResult


class HCAGAdapter:
    def __init__(self, graph: GraphStore):
        self.graph = graph
        self.planner: Any = FallbackPlanner()
        self.engine = "hcag_fallback_planner"
        self.window_store = ArcadeDBWindowStore(graph)
        self.context_store = ProjectContextStore()
        self.embedding_provider: Any = get_semantic_provider()
        self._last_route: dict[str, RouteResult] = {}
        self.backfill_status: dict[str, Any] = {"status": "not_started"}
        try:
            source_path = str(settings.hcag_path)
            if source_path not in sys.path:
                sys.path.insert(0, source_path)
            from hcag.routing import StructuredQueryPlanner

            self.planner = StructuredQueryPlanner()
            semantic = "semantic" if self.embedding_provider.semantic else "degraded_hash"
            # Keep the engine identifier stable for API/trace consumers. The
            # v3 adapter now routes company-memory domains and emits context gates.
            self.engine = f"hcag_hybrid_memory_arcadedb_v3_{semantic}"
        except Exception:
            pass

    def ingest_knowledge_item(self, item: dict[str, Any]) -> dict[str, Any]:
        route = self.route_query(
            item["project_id"],
            f"{item['source_title']}\n{item['content'][:1200]}",
            persist=False,
        )
        return {
            "domain": route.domain,
            "subdomain": route.subdomain,
            "context_window": route.context_window,
        }

    def index_chunk(self, text: str) -> dict[str, Any]:
        """Build stable, inspectable retrieval features for a durable chunk."""
        return self.index_chunks([text])[0]

    def index_chunks(self, texts: list[str]) -> list[dict[str, Any]]:
        """Batch dense inference while preserving inspectable sparse features."""
        embeddings = self.embedding_provider.embed_texts(texts)
        payloads: list[dict[str, Any]] = []
        for text, embedding in zip(texts, embeddings, strict=True):
            tokens = sorted(
                {token.casefold() for token in re.findall(r"[A-Za-z][A-Za-z0-9_.@/-]{2,}", text)}
            )
            payloads.append(
                {
                    "content_hash": sha256(" ".join(text.casefold().split()).encode()).hexdigest(),
                    "search_terms": tokens[:500],
                    "embedding": embedding,
                    "embedding_model": self.embedding_provider.model_name,
                    "embedding_version": self.embedding_provider.version,
                    "semantic_embedding": self.embedding_provider.semantic,
                }
            )
        return payloads

    def backfill_existing_chunks(self) -> dict[str, int]:
        """Upgrade legacy chunks into the traversable HCAG memory graph.

        The migration is idempotent and only touches chunks that predate the
        content hash/context-window index, so normal restarts stay cheap even
        for large company libraries.
        """
        from app.core.database import rows

        upgraded = linked = 0
        pending: list[dict[str, Any]] = []
        self.backfill_status = {"status": "running", "chunks_pending": 0}
        for project in rows("SELECT id FROM projects"):
            project_id = project["id"]
            for chunk in self.graph.list_nodes(project_id, "KnowledgeChunk", 100_000):
                if (
                    chunk.get("content_hash")
                    and chunk.get("context_window")
                    and chunk.get("embedding_model") == self.embedding_provider.model_name
                    and int(chunk.get("embedding_version") or 0) == self.embedding_provider.version
                ):
                    continue
                metadata_raw = chunk.get("metadata_json") or "{}"
                try:
                    metadata = (
                        json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                    )
                except json.JSONDecodeError:
                    metadata = {}
                route = metadata.get("hcag") or {}
                if not all(route.get(key) for key in ("domain", "subdomain")):
                    inferred = self.route_query(
                        project_id,
                        f"{chunk.get('source_title', '')}\n{chunk.get('text', '')[:1200]}",
                        persist=False,
                    )
                    route = {
                        "domain": inferred.domain,
                        "subdomain": inferred.subdomain,
                        "context_window": inferred.context_window,
                    }
                pending.append(
                    {
                        "chunk": chunk,
                        "project_id": project_id,
                        "route": route,
                        "needs_window_link": not bool(chunk.get("context_window")),
                        "embedding_text": f"{chunk.get('source_title', '')}\n{chunk.get('text', '')}",
                    }
                )
        self.backfill_status["chunks_pending"] = len(pending)
        features_batch = self.index_chunks([item["embedding_text"] for item in pending])
        for item, features in zip(pending, features_batch, strict=True):
            chunk = item["chunk"]
            project_id = item["project_id"]
            route = item["route"]
            self.graph.upsert_chunk(
                {
                    "id": chunk["id"],
                    "project_id": project_id,
                    "context_window": route.get("context_window")
                    or f"{route['domain']}.{route['subdomain']}",
                    "domain": route["domain"],
                    "subdomain": route["subdomain"],
                    "content_hash": features["content_hash"],
                    "search_terms": features["search_terms"],
                    "embedding": features.get("embedding", []),
                    "embedding_model": features.get("embedding_model", ""),
                    "embedding_version": features.get("embedding_version", 0),
                }
            )
            if item["needs_window_link"]:
                self.window_store.record_chunk(
                    project_id, route["domain"], route["subdomain"], chunk["id"]
                )
                linked += 1
            upgraded += 1
            self.backfill_status["chunks_upgraded"] = upgraded
        result = {"chunks_upgraded": upgraded, "window_links_created": linked}
        self.backfill_status = {"status": "complete", **result}
        return result

    def route_query(self, project_id: str, query: str, *, persist: bool = True) -> RouteResult:
        cleaned = re.sub(r"^\s*@(runbook|orgmemory)\b", "", query, flags=re.IGNORECASE).strip()

        service_match = re.search(r"\b([a-zA-Z][\w-]*(?:_service|-service))\b", cleaned)
        detected_service = service_match.group(1).lower() if service_match else None
        service_name, context_reused = self.context_store.resolve_service(
            project_id, cleaned, detected_service
        )
        resolved_query = self.context_store.enrich_query(cleaned, service_name, context_reused)
        lowered = resolved_query.lower()
        if any(term in lowered for term in ("policy", "allowed", "prohibited", "must")):
            subdomain = "policy_memory"
        elif any(term in lowered for term in ("decision", "decided", "why did", "chose")):
            subdomain = "decision_memory"
        elif any(term in lowered for term in ("owner", "owns", "responsible", "team")):
            subdomain = "ownership_memory"
        elif any(term in lowered for term in ("changed", "update", "current", "since")):
            subdomain = "temporal_memory"
        elif any(
            term in lowered for term in ("pipeline", "jenkins", "build", "deploy", "workflow")
        ):
            subdomain = "deployment_memory"
        elif any(
            term in lowered
            for term in ("fail", "error", "timeout", "incident", "outage", "root cause")
        ):
            subdomain = "incident_response"
        elif any(term in lowered for term in ("storage", "media", "volume", "backup")):
            subdomain = "service_memory"
        else:
            subdomain = "project_memory"
        raw_plan = self.planner.classify(resolved_query)
        plan = self._serialize_plan(raw_plan)
        query_type = str(plan.get("intent") or raw_plan).lower()
        previous_state = self.context_store.get(project_id)
        previous_window = previous_state.get("context_window", "") if persist else ""
        boundary = self.detect_boundary(previous_window, subdomain)
        context_window = f"company_memory.{subdomain}"
        route = RouteResult(
            domain="company_memory",
            subdomain=subdomain,
            context_window=context_window,
            query_type=query_type,
            service_name=service_name,
            boundary_type=boundary,
            confidence=0.9 if service_name else 0.78,
            resolved_query=resolved_query,
            context_reused=context_reused,
            query_count=int(previous_state.get("query_count") or 0),
            plan=plan,
        )
        if persist:
            state = self.context_store.record(
                project_id,
                domain=route.domain,
                subdomain=route.subdomain,
                context_window=route.context_window,
                service_name=route.service_name,
                boundary_type=route.boundary_type,
                query_type=route.query_type,
                query=cleaned,
                resolved_query=resolved_query,
            )
            route.query_count = int(state["query_count"])
            self._last_route[project_id] = route
        return route

    def ingest_source(self, item: dict[str, Any]) -> dict[str, Any]:
        return self.ingest_knowledge_item(item)

    def extract_memory_units(self, service: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return service.extract_memory_units(**kwargs)

    def index_memory_units(self, units: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.index_chunks([unit["content"] for unit in units]) if units else []

    def resolve_scope(
        self,
        project_id: str,
        query: str,
        *,
        principal_id: str = "",
        authorized_team_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        route = self.route_query(project_id, query, persist=False)
        return {
            "project_id": project_id,
            "service": route.service_name or "",
            "context_window": route.context_window,
            "principal_id": principal_id,
            "authorized_team_ids": authorized_team_ids or [],
            "security_boundary": (
                "team_allow_list" if authorized_team_ids is not None else "workspace_admin"
            ),
        }

    def retrieve_memory_context(self, project_id: str, query: str) -> list[GraphEvidence]:
        return self.retrieve_context(project_id, query)

    def assemble_context_profile(
        self,
        memory_service: Any,
        project_id: str,
        allowed_team_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        return memory_service.profile(project_id, allowed_team_ids=allowed_team_ids)

    def detect_updates(self, memory_service: Any, project_id: str) -> list[dict[str, Any]]:
        return memory_service.relationships(project_id, "UPDATES")

    def detect_conflicts(self, memory_service: Any, project_id: str) -> list[dict[str, Any]]:
        return memory_service.relationships(project_id, "CONTRADICTS")

    @staticmethod
    def _serialize_plan(plan: Any) -> dict[str, Any]:
        if isinstance(plan, str):
            return {"intent": plan, "reason_codes": ["fallback_planner"]}
        try:
            payload = asdict(plan)
        except (TypeError, ValueError):
            return {"intent": str(plan), "reason_codes": []}
        for key, value in list(payload.items()):
            if hasattr(value, "value"):
                payload[key] = value.value
        return payload

    def retrieve_context(
        self,
        project_id: str,
        query: str,
        service_name: str | None = None,
        route: RouteResult | None = None,
    ) -> list[GraphEvidence]:
        route = route or self.route_query(project_id, query)
        plan = plan_query(route.resolved_query or query)
        merged: dict[str, GraphEvidence] = {}
        matches: dict[str, list[str]] = {}
        for query_index, retrieval_query in enumerate(plan.retrieval_queries):
            weight = 1.0 if query_index == 0 else 0.9
            retrieved = self.graph.retrieve_context(
                project_id,
                retrieval_query,
                service_name or route.service_name,
                limit=18,
            )
            for rank, item in enumerate(retrieved):
                weighted_score = float(item.score or 0) * weight + max(0.0, 4.0 - rank * 0.15)
                current = merged.get(item.chunk_id)
                if current is None or weighted_score > current.score:
                    metadata = dict(item.metadata)
                    metadata["universal_query_plan"] = plan.trace()
                    merged[item.chunk_id] = replace(
                        item,
                        metadata=metadata,
                        score=weighted_score,
                    )
                matches.setdefault(item.chunk_id, []).append(retrieval_query)
        for chunk_id, item in merged.items():
            matched_queries = list(dict.fromkeys(matches.get(chunk_id, [])))
            item.metadata["matched_query_variants"] = matched_queries
            item.score += min(10.0, max(0, len(matched_queries) - 1) * 2.5)
        return sorted(merged.values(), key=lambda item: item.score, reverse=True)[:24]

    def detect_boundary(self, previous_query: str, current_query: str) -> str:
        if not previous_query:
            return "none"
        previous = previous_query.rsplit(".", 1)[-1]
        current = current_query.rsplit(".", 1)[-1]
        if previous == current:
            return "none"
        operational = {
            "incident_response",
            "deployment_memory",
            "service_memory",
            "policy_memory",
            "decision_memory",
            "ownership_memory",
            "temporal_memory",
        }
        return "soft" if previous in operational and current in operational else "hard"

    def build_retrieval_trace(
        self,
        project_id: str,
        query: str,
        evidence: list[GraphEvidence],
        *,
        route: RouteResult | None = None,
    ) -> HCAGTrace:
        # The service passes its request-local route. Falling back to the cache
        # is retained for compatibility, but must not be used by concurrent API
        # requests because another query can update the same project route.
        route = route or self._last_route.get(project_id) or self.route_query(project_id, query)
        graph_paths = self.graph.get_retrieval_trace(
            project_id, [item.chunk_id for item in evidence]
        )
        confidences = sorted(
            (float(item.metadata.get("retrieval_confidence", 0.0)) for item in evidence),
            reverse=True,
        )
        strongest = confidences[:3]
        lane_counts = Counter(
            str(item.metadata.get("primary_lane") or "sparse_exact") for item in evidence
        )
        plan = dict(route.plan)
        compiled_context = plan.pop("_compiled_context", {}) or {}
        swarm_runs = plan.pop("_swarm_runs", []) or []
        active_activation_run_id = plan.pop("_active_activation_run_id", "") or ""
        plan.update(
            {
                "retrieval_strategy": "semantic_vector_cross_encoder_temporal_v2",
                "activation_strategy": (
                    "biological_context_swarm_v1" if swarm_runs else "single_retriever"
                ),
                "retrieval_lanes": dict(lane_counts),
                "memory_dynamics": "ingestion_driven_fast_slow",
                "attention_note": "Application retrieval inspired by compressed attention; not a model attention kernel.",
                "context_gates": [
                    "authorized_team_scope",
                    "task_relevance",
                    "temporal_currentness",
                    "entity_graph_neighborhood",
                    "token_budget",
                ],
            }
        )
        if swarm_runs:
            plan["context_activation_swarm"] = {
                "version": "biological_context_swarm_v1",
                "active_run_id": active_activation_run_id,
                "run_count": len(swarm_runs),
                "runs": swarm_runs,
                "compiled_context": {
                    "format": compiled_context.get("format", ""),
                    "token_budget": compiled_context.get("token_budget", 0),
                    "evidence_token_budget": compiled_context.get("evidence_token_budget", 0),
                    "token_count": compiled_context.get("token_count", 0),
                    "selected_evidence_ids": compiled_context.get("selected_evidence_ids", []),
                    "source_ids": compiled_context.get("source_ids", []),
                    "omitted_candidate_count": compiled_context.get("omitted_candidate_count", 0),
                },
            }
        confidence = (
            round(0.55 * strongest[0] + 0.45 * (sum(strongest) / len(strongest)), 3)
            if strongest
            else 0.0
        )
        return HCAGTrace(
            domain=route.domain,
            subdomain=route.subdomain,
            context_window=route.context_window,
            boundary_type=route.boundary_type,
            query_type=route.query_type,
            retrieved_chunk_ids=[item.chunk_id for item in evidence],
            graph_paths=graph_paths,
            confidence=confidence,
            engine=self.engine,
            resolved_query=route.resolved_query,
            context_reused=route.context_reused,
            query_count=route.query_count,
            plan=plan,
        )
