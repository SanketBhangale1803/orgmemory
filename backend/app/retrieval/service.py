from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from app.audit import AuditService
from app.core.database import rows
from app.graph.base import GraphEvidence
from app.graph.graph_explainer import explain_paths
from app.hcag_adapter import HCAGAdapter
from app.hcag_adapter.models import RouteResult
from app.intelligence.correlation import correlate_changes
from app.intelligence.trust import trust_score

from .hypotheses import extract_hypotheses
from .reasoner import evidence_answer, llm_answer

# Below this final confidence, the diagnostic hypothesis path engages (in addition
# to whenever the reasoner reports insufficient evidence). Prototype constant; can
# be promoted to settings once the loop is validated.
LOW_CONFIDENCE_THRESHOLD = 0.45


def should_run_diagnostics(route: RouteResult, sufficient: bool, confidence: float) -> bool:
    """Gate the Stage 1 diagnostic path to the service-down failure class only."""
    if not (route.service_name and route.subdomain == "incident_response"):
        return False
    return (not sufficient) or confidence < LOW_CONFIDENCE_THRESHOLD


class RetrievalService:
    def __init__(self, hcag: HCAGAdapter, audit: AuditService | None = None):
        self.hcag = hcag
        self.audit = audit or AuditService()

    def ask(self, project_id: str, query: str) -> dict[str, Any]:
        route = self.hcag.route_query(project_id, query)
        evidence = self.hcag.retrieve_context(project_id, query, route.service_name)
        grounded = llm_answer(query, evidence) or evidence_answer(query, evidence)
        trace = asdict(self.hcag.build_retrieval_trace(project_id, query, evidence))
        trace["graph_path_explanations"] = explain_paths(trace.get("graph_paths", []))
        citations = self._citations(evidence) if grounded["sufficient"] else []
        service_counts = Counter(name for item in evidence[:8] for name in item.service_names)
        services = sorted(
            name
            for name, count in service_counts.items()
            if count >= 2 or name == route.service_name
        )
        confidence = (
            trace["confidence"] if grounded["sufficient"] else min(trace["confidence"], 0.25)
        )
        runbooks = self._suggested_runbooks(project_id, query, services)
        related = (
            self._related_sources(evidence)
            if grounded["sufficient"]
            else {"files": [], "issues": [], "pull_requests": [], "slack_messages": []}
        )
        trust = (
            trust_score(project_id, evidence)
            if grounded["sufficient"]
            else {
                "score": 0.0,
                "level": "none",
                "reason": "No sufficiently supported answer, so no trust is asserted.",
                "factors": {},
                "contradictions": [],
            }
        )
        result = {
            "answer": grounded["answer"],
            "likely_cause": grounded["likely_cause"],
            "confidence": confidence,
            "trust_score": trust,
            "related_services": services,
            "related_files": related["files"],
            "related_issues": related["issues"],
            "related_pull_requests": related["pull_requests"],
            "related_slack_messages": related["slack_messages"],
            "evidence": citations,
            "retrieval_trace": trace,
            "suggested_runbooks": runbooks,
            "safe_actions": grounded.get("safe_actions", []),
            "approval_required": grounded.get("approval_required", []),
        }
        if route.subdomain == "incident_response" and evidence:
            correlation = correlate_changes(project_id, evidence, route.service_name)
            if correlation["suspects"]:
                result["change_correlation"] = correlation
        if should_run_diagnostics(route, grounded["sufficient"], confidence):
            hypotheses = extract_hypotheses(
                self.hcag.graph, project_id, route.service_name, evidence
            )
            result["hypotheses"] = hypotheses
            self.audit.record(
                "diagnostic.hypotheses_generated",
                query,
                project_id,
                payload={
                    "count": len(hypotheses),
                    "hypothesis_ids": [item["id"] for item in hypotheses],
                    "confidence": confidence,
                },
            )
        self.audit.record(
            "query.answered",
            query,
            project_id,
            payload={
                "confidence": confidence,
                "evidence_ids": [item.chunk_id for item in evidence],
                "answer": grounded["answer"],
            },
        )
        return result

    @staticmethod
    def _citation(item: GraphEvidence) -> dict[str, Any]:
        snippet = item.text.replace("\n", " ").strip()
        return {
            "chunk_id": item.chunk_id,
            "source_type": item.source_type,
            "source_title": item.source_title,
            "source_url": item.source_url,
            "snippet": snippet[:420] + ("…" if len(snippet) > 420 else ""),
            "confidence": item.metadata.get("retrieval_confidence", 0.0),
        }

    @classmethod
    def _citations(cls, evidence: list[GraphEvidence]) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for item in evidence:
            identity = (item.source_title, item.source_url)
            if identity in seen:
                continue
            seen.add(identity)
            citations.append(cls._citation(item))
            if len(citations) == 8:
                break
        return citations

    @staticmethod
    def _related_sources(evidence: list[GraphEvidence]) -> dict[str, list[dict[str, str]]]:
        """Group retrieved evidence by source type into related files/issues/PRs.

        Strictly derived from the ranked evidence so nothing is asserted that the
        retrieval pass did not actually surface.
        """
        buckets: dict[str, list[dict[str, str]]] = {
            "files": [],
            "issues": [],
            "pull_requests": [],
            "slack_messages": [],
        }
        keys = {
            "repo_file": "files",
            "github_issue": "issues",
            "pull_request": "pull_requests",
            "slack": "slack_messages",
            "slack_export": "slack_messages",
        }
        seen: set[tuple[str, str]] = set()
        for item in evidence:
            bucket = keys.get(item.source_type)
            if not bucket:
                continue
            identity = (bucket, item.source_title)
            if identity in seen:
                continue
            seen.add(identity)
            buckets[bucket].append({"title": item.source_title, "url": item.source_url})
        return {key: value[:6] for key, value in buckets.items()}

    @staticmethod
    def _suggested_runbooks(project_id: str, query: str, services: list[str]) -> list[str]:
        records = rows(
            "SELECT runbook_key,payload_json FROM runbooks WHERE project_id=?", (project_id,)
        )
        terms = set(query.lower().replace("_", " ").split()) | {
            service.lower() for service in services
        }
        terms -= {"runbook", "service", "failing", "failure", "this", "that", "why", "what", "how"}
        suggestions: list[str] = []
        for record in records:
            searchable = record["payload_json"].lower().replace("_", " ")
            if any(term in searchable for term in terms if len(term) > 3):
                suggestions.append(record["runbook_key"])
        return suggestions[:5]
