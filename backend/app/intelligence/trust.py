"""Trust scoring for answers and runbooks.

A trust score is not the same as retrieval confidence. Retrieval confidence
measures how well evidence matched the query; trust measures how much the
evidence itself deserves to be believed: source quality, ingestion recency
(the only honest time axis for local corpora), breadth of independent
support, and detected contradictions between cause statements.

Every factor is computed from data Runbook actually holds. Nothing here
invents freshness or agreement that was not observed.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.core.database import rows
from app.graph.base import GraphEvidence

# Relative believability of a source type for operational questions. Current
# repository state outranks discussion; discussion outranks unlabeled text.
SOURCE_QUALITY = {
    "repo_file": 0.90,
    "incident": 0.85,
    "github_issue": 0.80,
    "pull_request": 0.80,
    "log": 0.75,
    "doc": 0.70,
    "slack": 0.65,
    "slack_export": 0.65,
}
DEFAULT_QUALITY = 0.55

CAUSE_RE = re.compile(r"(?i)(?:root cause|caused by|because|due to)[:\s]+(.{8,200})")
SIGNAL_TOKEN_RE = re.compile(
    r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+|[a-z][\w-]*(?:_service|-service))\b"
)


def _ingestion_ages_days(project_id: str) -> dict[str, float]:
    """Map knowledge_item id -> age in days since ingestion."""
    now = datetime.now(UTC)
    ages: dict[str, float] = {}
    for record in rows(
        "SELECT id, created_at FROM knowledge_items WHERE project_id=?", (project_id,)
    ):
        try:
            created = datetime.fromisoformat(record["created_at"])
            ages[record["id"]] = max(0.0, (now - created).total_seconds() / 86400)
        except (ValueError, TypeError):
            continue
    return ages


def detect_contradictions(evidence: list[GraphEvidence]) -> list[dict[str, Any]]:
    """Find pairs of sources whose explicit cause statements name disjoint signals.

    Two cause sentences contradict only when both make an explicit causal claim
    and the technical tokens they blame (env vars, services) do not overlap.
    Absence of overlap in plain prose is not treated as contradiction.
    """
    claims: list[tuple[str, str, set[str]]] = []
    for item in evidence[:10]:
        for match in CAUSE_RE.finditer(item.text):
            statement = match.group(1).strip()
            tokens = set(SIGNAL_TOKEN_RE.findall(statement))
            if tokens:
                claims.append((item.source_title, statement, tokens))
                break
    contradictions: list[dict[str, Any]] = []
    for index, (title_a, claim_a, tokens_a) in enumerate(claims):
        for title_b, claim_b, tokens_b in claims[index + 1 :]:
            if title_a != title_b and not (tokens_a & tokens_b):
                contradictions.append(
                    {
                        "source_a": title_a,
                        "claim_a": claim_a[:160],
                        "source_b": title_b,
                        "claim_b": claim_b[:160],
                    }
                )
    return contradictions[:3]


def trust_score(project_id: str, evidence: list[GraphEvidence]) -> dict[str, Any]:
    """Score 0..1 with explicit factors and a human-readable reason."""
    if not evidence:
        return {
            "score": 0.0,
            "level": "none",
            "reason": "No evidence was retrieved, so there is nothing to trust.",
            "factors": {},
            "contradictions": [],
        }
    top = evidence[:8]
    quality = sum(SOURCE_QUALITY.get(item.source_type, DEFAULT_QUALITY) for item in top) / len(top)

    ages = _ingestion_ages_days(project_id)
    item_ages = [
        ages[item.metadata.get("item_id", "")]
        for item in top
        if item.metadata.get("item_id", "") in ages
    ]
    # 1.0 for evidence ingested within a week, decaying to 0.4 at ~90 days.
    if item_ages:
        avg_age = sum(item_ages) / len(item_ages)
        recency = max(0.4, 1.0 - min(avg_age, 90.0) / 150.0)
    else:
        avg_age = None
        recency = 0.6  # unknown age: neither penalize hard nor reward

    distinct_sources = len({(item.source_type, item.source_title) for item in top})
    support = min(1.0, 0.4 + 0.15 * distinct_sources)

    distinct_types = len({item.source_type for item in top})
    cross_source = min(1.0, 0.6 + 0.2 * (distinct_types - 1)) if distinct_types else 0.6

    contradictions = detect_contradictions(evidence)
    contradiction_penalty = 0.15 * len(contradictions)

    score = round(
        max(
            0.0,
            0.35 * quality
            + 0.25 * recency
            + 0.25 * support
            + 0.15 * cross_source
            - contradiction_penalty,
        ),
        3,
    )
    level = "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"

    parts = [
        f"{distinct_sources} distinct source{'s' if distinct_sources != 1 else ''} "
        f"across {distinct_types} source type{'s' if distinct_types != 1 else ''}"
    ]
    if avg_age is not None:
        parts.append(f"average evidence age {avg_age:.0f} day(s) since ingestion")
    else:
        parts.append("evidence age unknown")
    if contradictions:
        parts.append(f"{len(contradictions)} contradicting cause statement pair(s) detected")
    else:
        parts.append("no contradicting cause statements detected")
    return {
        "score": score,
        "level": level,
        "reason": "; ".join(parts) + ".",
        "factors": {
            "source_quality": round(quality, 3),
            "recency": round(recency, 3),
            "support_breadth": round(support, 3),
            "cross_source_agreement": round(cross_source, 3),
            "contradiction_penalty": round(contradiction_penalty, 3),
            "recency_basis": "ingestion_time",
        },
        "contradictions": contradictions,
    }
