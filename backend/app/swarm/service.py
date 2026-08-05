"""Concurrent specialist retrieval with one security-aware context compiler.

The specialists are deterministic today so retrieval remains testable and
auditable. Their contract is intentionally agent-shaped: each worker receives
only a query, route, project boundary, and authorization boundary, and returns
typed evidence. A model-backed specialist can implement the same contract
later without changing the compiler or answer pipeline.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from time import monotonic
from typing import Any

from app.core.database import connect, new_id, rows, utcnow
from app.governance import ScopeService
from app.graph.base import GraphEvidence
from app.hcag_adapter import HCAGAdapter
from app.hcag_adapter.models import RouteResult
from app.intelligence.trust import detect_contradictions
from app.memory.company import CompanyMemoryService

from .models import AgentReport, CompiledActivation

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.@/-]{2,}")
STOP_WORDS = {
    "about",
    "after",
    "before",
    "does",
    "explain",
    "from",
    "have",
    "into",
    "that",
    "their",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
}


class ContextActivationSwarm:
    """Coordinate foragers, critic, and a single bounded context compiler."""

    VERSION = "biological_context_swarm_v1"

    def __init__(self, hcag: HCAGAdapter):
        self.hcag = hcag
        self.graph = hcag.graph
        self.scopes = ScopeService()

    def collect_project(
        self,
        project_id: str,
        query: str,
        route: RouteResult,
        *,
        allowed_team_ids: list[str] | None,
    ) -> list[AgentReport]:
        """Run isolated specialists concurrently; one failure cannot kill the swarm."""

        jobs: list[tuple[str, str, Callable[[], list[GraphEvidence]]]] = [
            (
                "sensory_activation",
                "hybrid semantic, lexical, and temporal activation",
                lambda: self.hcag.retrieve_context(
                    project_id,
                    query,
                    route.service_name,
                    route=route,
                ),
            ),
            (
                "graph_forager",
                "bounded query-seeded relationship traversal",
                lambda: self.graph.traverse_context(
                    project_id,
                    route.resolved_query or query,
                    max_hops=self._required_hops(route),
                    limit=18,
                ),
            ),
            (
                "current_truth_historian",
                "current atomic-memory and source activation",
                lambda: self._current_truth_evidence(
                    project_id,
                    query,
                    allowed_team_ids=allowed_team_ids,
                ),
            ),
        ]
        reports: list[AgentReport] = []
        with ThreadPoolExecutor(
            max_workers=len(jobs), thread_name_prefix="context-activation"
        ) as executor:
            futures = {
                executor.submit(self._run_agent, project_id, allowed_team_ids, job): job
                for job in jobs
            }
            for future in as_completed(futures):
                agent, role, _worker = futures[future]
                try:
                    reports.append(future.result())
                except Exception as exc:  # pragma: no cover - defensive around executor failures
                    reports.append(
                        AgentReport(
                            agent=agent,
                            role=role,
                            project_id=project_id,
                            status="failed",
                            error=self._safe_error(exc),
                        )
                    )
        return sorted(reports, key=lambda report: report.agent)

    def specialist_report(
        self,
        agent: str,
        role: str,
        project_id: str,
        candidates: list[GraphEvidence],
        *,
        allowed_team_ids: list[str] | None,
    ) -> AgentReport:
        """Admit a deterministic domain specialist through the same security gate."""

        started = monotonic()
        scoped = self._security_trim(
            candidates,
            default_project_id=project_id,
            allowed_team_ids=allowed_team_ids,
        )
        for item in scoped:
            contributors = list(item.metadata.get("swarm_agents") or [])
            item.metadata["swarm_agents"] = list(dict.fromkeys([*contributors, agent]))
        return AgentReport(
            agent=agent,
            role=role,
            project_id=project_id,
            status="complete",
            candidates=scoped,
            latency_ms=round((monotonic() - started) * 1000),
            details={
                "authorization_trimmed_before_compilation": True,
                "security_boundary": (
                    "team_allow_list" if allowed_team_ids is not None else "workspace_admin"
                ),
            },
        )

    def compile(
        self,
        project_id: str,
        query: str,
        reports: list[AgentReport],
        *,
        principal_id: str,
        token_budget: int,
        max_items: int = 16,
    ) -> CompiledActivation:
        """Critique candidates and create the one context presented downstream."""

        started_at = utcnow()
        run_id = new_id("swarm")
        accepted, critic = self._critic(reports)
        evidence, compiled = self._compile_context(
            accepted,
            run_id=run_id,
            token_budget=token_budget,
            max_items=max_items,
        )
        summaries = [report.public_summary() for report in reports]
        failed_agents = [report["agent"] for report in summaries if report["status"] == "failed"]
        status = "degraded" if failed_agents else "complete"
        trace = {
            "run_id": run_id,
            "version": self.VERSION,
            "status": status,
            "agents": summaries,
            "critic": critic,
            "compiler": {
                "selected_evidence_ids": compiled["selected_evidence_ids"],
                "selected_source_ids": compiled["source_ids"],
                "token_budget": compiled["token_budget"],
                "evidence_token_budget": compiled["evidence_token_budget"],
                "compiled_token_count": compiled["token_count"],
                "reserved_response_tokens": compiled["reserved_response_tokens"],
                "omitted_candidate_count": compiled["omitted_candidate_count"],
            },
            "failed_agents": failed_agents,
        }
        completed_at = utcnow()
        with connect() as conn:
            conn.execute(
                """INSERT INTO context_activation_runs (
                  id,project_id,principal_id,query,status,token_budget,
                  selected_evidence_ids_json,compiled_context_json,agent_reports_json,
                  trace_json,created_at,completed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    project_id,
                    principal_id,
                    query,
                    status,
                    max(1, int(token_budget)),
                    json.dumps(compiled["selected_evidence_ids"]),
                    json.dumps(compiled),
                    json.dumps(summaries),
                    json.dumps(trace),
                    started_at,
                    completed_at,
                ),
            )
        return CompiledActivation(
            run_id=run_id,
            evidence=evidence,
            compiled_context=compiled,
            trace=trace,
        )

    def _run_agent(
        self,
        project_id: str,
        allowed_team_ids: list[str] | None,
        job: tuple[str, str, Callable[[], list[GraphEvidence]]],
    ) -> AgentReport:
        agent, role, worker = job
        started = monotonic()
        try:
            candidates = self._security_trim(
                worker(),
                default_project_id=project_id,
                allowed_team_ids=allowed_team_ids,
            )
            for item in candidates:
                contributors = list(item.metadata.get("swarm_agents") or [])
                item.metadata["swarm_agents"] = list(dict.fromkeys([*contributors, agent]))
            return AgentReport(
                agent=agent,
                role=role,
                project_id=project_id,
                status="complete",
                candidates=candidates,
                latency_ms=round((monotonic() - started) * 1000),
                details={
                    "authorization_trimmed_before_compilation": True,
                    "security_boundary": (
                        "team_allow_list" if allowed_team_ids is not None else "workspace_admin"
                    ),
                },
            )
        except Exception as exc:
            return AgentReport(
                agent=agent,
                role=role,
                project_id=project_id,
                status="failed",
                latency_ms=round((monotonic() - started) * 1000),
                error=self._safe_error(exc),
            )

    def _security_trim(
        self,
        evidence: list[GraphEvidence],
        *,
        default_project_id: str,
        allowed_team_ids: list[str] | None,
    ) -> list[GraphEvidence]:
        if allowed_team_ids is None:
            return evidence
        grouped: dict[str, list[GraphEvidence]] = {}
        for item in evidence:
            source_project = str(item.metadata.get("project_id") or default_project_id)
            grouped.setdefault(source_project, []).append(item)
        visible: list[GraphEvidence] = []
        for source_project, candidates in grouped.items():
            source_ids = {
                str(item.metadata.get("source_id") or "")
                for item in candidates
                if item.metadata.get("source_id")
            }
            allowed_sources = self.scopes.visible_source_ids(
                source_project, source_ids, allowed_team_ids
            )
            visible.extend(
                item
                for item in candidates
                if not item.metadata.get("source_id")
                or str(item.metadata["source_id"]) in allowed_sources
            )
        return visible

    def _current_truth_evidence(
        self,
        project_id: str,
        query: str,
        *,
        allowed_team_ids: list[str] | None,
    ) -> list[GraphEvidence]:
        memories = CompanyMemoryService(self.graph).list(
            project_id,
            latest=True,
            limit=500,
            allowed_team_ids=allowed_team_ids,
        )
        terms = self._terms(query)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for memory in memories:
            searchable = (
                f"{memory.get('type', '')} {memory.get('subject', '')} "
                f"{memory.get('content', '')}"
            ).casefold()
            overlap = sum(term in searchable for term in terms)
            temporal_boost = (
                2
                if any(
                    marker in query.casefold()
                    for marker in ("current", "latest", "now", "changed", "decision", "policy")
                )
                else 0
            )
            if overlap or not terms:
                ranked.append(
                    (
                        overlap * 4.0 + temporal_boost + float(memory.get("confidence") or 0),
                        memory,
                    )
                )
        ranked.sort(key=lambda value: value[0], reverse=True)
        output: list[GraphEvidence] = []
        for score, memory in ranked[:12]:
            source_ids = list(memory.get("source_ids") or [])
            for source_id in source_ids[:3] or [""]:
                source = self._latest_source(project_id, source_id)
                text = str((source or {}).get("content") or memory.get("content") or "")
                if not text:
                    continue
                metadata = self._metadata((source or {}).get("metadata_json"))
                metadata.update(
                    {
                        "project_id": project_id,
                        "source_id": source_id,
                        "item_id": (source or {}).get("id", ""),
                        "memory_id": memory["id"],
                        "memory_type": memory.get("type", ""),
                        "primary_lane": "current_truth",
                        "retrieval_confidence": min(
                            0.94, max(0.55, float(memory.get("confidence") or 0.6))
                        ),
                        "retrieval_lanes": {"current_truth": round(score, 3)},
                        "score_components": {"current_truth": round(score, 3)},
                        "current_truth": True,
                    }
                )
                output.append(
                    GraphEvidence(
                        chunk_id=(
                            f"current-truth:{memory['id']}:{(source or {}).get('id', source_id)}"
                        ),
                        text=text,
                        source_type=str((source or {}).get("source_type") or "memory"),
                        source_title=str(
                            (source or {}).get("source_title")
                            or memory.get("subject")
                            or "Current memory"
                        ),
                        source_url=str((source or {}).get("source_url") or ""),
                        service_names=list(metadata.get("service_names") or []),
                        metadata=metadata,
                        score=score + 2.0,
                        graph_paths=[f"{memory['id']} → MEMORY_DERIVED_FROM_SOURCE:{source_id}"],
                    )
                )
        return output

    @staticmethod
    def _latest_source(project_id: str, source_id: str) -> dict[str, Any] | None:
        if not source_id:
            return None
        records = rows(
            """SELECT * FROM knowledge_items WHERE project_id=? AND source_id=?
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, source_id),
        )
        return records[0] if records else None

    @staticmethod
    def _critic(
        reports: list[AgentReport],
    ) -> tuple[list[GraphEvidence], dict[str, Any]]:
        merged: dict[str, GraphEvidence] = {}
        rejected: list[dict[str, str]] = []
        content_seen: dict[str, str] = {}
        candidate_count = 0
        for report in reports:
            if report.status != "complete":
                continue
            for item in report.candidates:
                candidate_count += 1
                if not item.text.strip():
                    rejected.append({"evidence_id": item.chunk_id, "reason": "empty_evidence"})
                    continue
                fingerprint = " ".join(item.text.casefold().split())[:1000]
                duplicate_id = content_seen.get(fingerprint)
                if duplicate_id and duplicate_id != item.chunk_id:
                    rejected.append(
                        {
                            "evidence_id": item.chunk_id,
                            "reason": f"duplicate_content:{duplicate_id}",
                        }
                    )
                    existing = merged.get(duplicate_id)
                    if existing:
                        agents = list(
                            dict.fromkeys(
                                [
                                    *list(existing.metadata.get("swarm_agents") or []),
                                    *list(item.metadata.get("swarm_agents") or []),
                                ]
                            )
                        )
                        winner = item if item.score > existing.score else existing
                        winner.metadata["swarm_agents"] = agents
                        winner.metadata["swarm_consensus"] = len(agents)
                        winner.score = max(item.score, existing.score) + min(4.0, len(agents) - 1)
                        if winner.chunk_id != duplicate_id:
                            merged.pop(duplicate_id, None)
                            merged[winner.chunk_id] = winner
                            content_seen[fingerprint] = winner.chunk_id
                    continue
                content_seen[fingerprint] = item.chunk_id
                current = merged.get(item.chunk_id)
                if current is None:
                    merged[item.chunk_id] = item
                    continue
                agents = list(
                    dict.fromkeys(
                        [
                            *list(current.metadata.get("swarm_agents") or []),
                            *list(item.metadata.get("swarm_agents") or []),
                        ]
                    )
                )
                winner = item if item.score > current.score else current
                winner.metadata["swarm_agents"] = agents
                winner.metadata["swarm_consensus"] = len(agents)
                winner.score = max(item.score, current.score) + min(4.0, len(agents) - 1)
                merged[item.chunk_id] = winner
        accepted = sorted(merged.values(), key=lambda item: item.score, reverse=True)
        contradictions = detect_contradictions(accepted)
        return accepted, {
            "candidate_count": candidate_count,
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "rejections": rejected[:20],
            "contradictions": contradictions,
            "policy": "source-backed, non-empty, content-deduplicated, consensus-boosted",
        }

    @staticmethod
    def _compile_context(
        candidates: list[GraphEvidence],
        *,
        run_id: str,
        token_budget: int,
        max_items: int,
    ) -> tuple[list[GraphEvidence], dict[str, Any]]:
        budget = max(1, int(token_budget))
        reserve = min(1000, max(1, budget // 5))
        evidence_budget = max(1, budget - reserve)
        selected: list[GraphEvidence] = []
        consumed = 0
        remaining = list(candidates)

        # Seed source diversity before greedily filling by score.
        ordered: list[GraphEvidence] = []
        seen_sources: set[tuple[str, str]] = set()
        for item in remaining:
            key = (item.source_type, item.source_title)
            if key not in seen_sources:
                ordered.append(item)
                seen_sources.add(key)
        ordered.extend(item for item in remaining if item not in ordered)

        for candidate in ordered:
            if len(selected) >= max_items or consumed >= evidence_budget:
                break
            header = f"[S{len(selected) + 1}] {candidate.source_title} ({candidate.source_type})\n"
            separator_tokens = ContextActivationSwarm._estimate_tokens("\n\n") if selected else 0
            overhead = ContextActivationSwarm._estimate_tokens(header) + separator_tokens
            available = evidence_budget - consumed - overhead
            if available <= 0:
                break
            original_tokens = ContextActivationSwarm._estimate_tokens(candidate.text)
            item = candidate
            content_tokens = min(original_tokens, available)
            if content_tokens < original_tokens:
                character_limit = max(1, content_tokens * 4)
                metadata = dict(candidate.metadata)
                metadata.update(
                    {
                        "context_truncated": True,
                        "original_token_count": original_tokens,
                    }
                )
                item = replace(
                    candidate,
                    text=candidate.text[:character_limit].rstrip(),
                    metadata=metadata,
                )
                content_tokens = ContextActivationSwarm._estimate_tokens(item.text)
            if not item.text:
                continue
            token_count = overhead + content_tokens
            item.metadata.update(
                {
                    "swarm_run_id": run_id,
                    "context_position": len(selected) + 1,
                    "context_token_count": token_count,
                }
            )
            selected.append(item)
            consumed += token_count

        content = "\n\n".join(
            f"[S{index}] {item.source_title} ({item.source_type})\n{item.text}"
            for index, item in enumerate(selected, start=1)
        )
        actual_token_count = ContextActivationSwarm._estimate_tokens(content)
        source_ids = list(
            dict.fromkeys(
                str(item.metadata.get("source_id") or "")
                for item in selected
                if item.metadata.get("source_id")
            )
        )
        compiled = {
            "format": "orgmemory_compiled_context_v1",
            "run_id": run_id,
            "content": content,
            "token_budget": budget,
            "evidence_token_budget": evidence_budget,
            "reserved_response_tokens": reserve,
            "token_count": actual_token_count,
            "selected_evidence_ids": [item.chunk_id for item in selected],
            "source_ids": source_ids,
            "omitted_candidate_count": max(0, len(candidates) - len(selected)),
        }
        return selected, compiled

    @staticmethod
    def _required_hops(route: RouteResult) -> int:
        raw = route.plan.get("required_hops", route.plan.get("max_hops", 3))
        try:
            return max(1, min(int(raw), 5))
        except (TypeError, ValueError):
            return 3

    @staticmethod
    def _terms(query: str) -> set[str]:
        return {
            token.casefold()
            for token in TOKEN_RE.findall(query)
            if token.casefold() not in STOP_WORDS
        }

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, (len(text) + 3) // 4) if text else 0

    @staticmethod
    def _metadata(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        try:
            return json.loads(value or "{}")
        except (TypeError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        return f"{type(exc).__name__}: {str(exc)[:240]}"
