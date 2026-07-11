"""Evidence ranking for graph retrieval.

Hybrid scoring over project knowledge chunks: lexical term overlap weighted
by frequency, a strong boost for chunks tied to the routed service, a boost
for operational source types, and an overview path for repository-level
questions. Confidence is normalized against the best-scoring chunk so it
reflects relative support within this retrieval, not an absolute claim.

This module is the single ranking implementation used by both the ArcadeDB
store and the in-memory test store, and it is the seam where an
embedding-based scorer can be added without changing response contracts.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from .base import GraphEvidence

TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_.-]{2,}")
STOP = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "why",
    "how",
    "what",
    "runbook",
    "this",
    "that",
    "service",
}
OVERVIEW_TERMS = {
    "about",
    "application",
    "describe",
    "does",
    "overview",
    "project",
    "purpose",
    "repo",
    "repository",
    "work",
}
OVERVIEW_PHRASES = (
    "what is this",
    "what does this",
    "what is the project",
    "what is the service",
    "what does it do",
    "tell me about",
    "project overview",
    "service overview",
    "describe this",
)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOP]


def _overview_intent(query: str) -> bool:
    lowered = " ".join(query.lower().replace("@runbook", "").split())
    terms = set(_tokens(lowered))
    return any(phrase in lowered for phrase in OVERVIEW_PHRASES) or (
        bool(terms) and terms <= OVERVIEW_TERMS
    )


def rank_records(
    records: list[dict[str, Any]], query: str, service_name: str | None, limit: int
) -> list[GraphEvidence]:
    query_terms = Counter(_tokens(query))
    overview = _overview_intent(query)
    ranked: list[GraphEvidence] = []
    for record in records:
        haystack = f"{record.get('source_title', '')} {record.get('text', '')}".lower()
        haystack_terms = Counter(_tokens(haystack))
        matched = [term for term in query_terms if term in haystack_terms]
        lexical = sum(
            (1 + min(haystack_terms[term], 4)) * weight
            for term, weight in query_terms.items()
            if term in haystack_terms
        )
        raw_services = record.get("service_names") or "[]"
        services = json.loads(raw_services) if isinstance(raw_services, str) else raw_services
        service_boost = (
            10
            if service_name and service_name.lower() in {str(value).lower() for value in services}
            else 0
        )
        source_boost = (
            2
            if (lexical or service_boost)
            and record.get("source_type")
            in {"github_issue", "pull_request", "slack", "incident", "log"}
            else 0
        )
        metadata_raw = record.get("metadata_json") or "{}"
        metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
        overview_score = 0
        if overview and not lexical and not service_boost:
            title = str(record.get("source_title", "")).lower()
            chunk_index = int(metadata.get("chunk_index", 0))
            if title in {"readme.md", "readme", "readme.txt"}:
                overview_score = max(12, 22 - chunk_index)
            elif title in {"package.json", "pyproject.toml", "cargo.toml", "go.mod"}:
                overview_score = 12
            elif title.endswith(("deployment.md", "architecture.md", "overview.md")):
                overview_score = 10
            elif record.get("source_type") == "repo_file" and title.endswith(".md"):
                overview_score = 6
        score = lexical + service_boost + source_boost + overview_score
        if score <= 0:
            continue
        metadata["matched_terms"] = matched or (["project_overview"] if overview_score else [])
        ranked.append(
            GraphEvidence(
                chunk_id=record["id"],
                text=record.get("text", ""),
                source_type=record.get("source_type", "unknown"),
                source_title=record.get("source_title", "Untitled source"),
                source_url=record.get("source_url", ""),
                service_names=list(services or []),
                metadata=metadata,
                score=float(score),
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)
    top = ranked[0].score if ranked else 1.0
    for evidence in ranked:
        evidence.metadata["retrieval_confidence"] = round(
            min(0.96, 0.25 + 0.45 * evidence.score / top + 0.3 * min(1.0, evidence.score / 18)), 3
        )
    return ranked[:limit]
