"""Stage 1 diagnostic hypothesis extraction (Option A).

Scope is intentionally narrow: the service-down / service-erroring failure class
only. Hypotheses are derived from evidence that the graph genuinely holds today
(KnowledgeChunk nodes, their stored error signals, CHUNK_REFERENCES_SERVICE, and
SERVICE_DEPENDS_ON_SERVICE / SERVICE_USES_ENV_VAR edges where repo ingestion
created them). We do NOT model recent-deploy or resource-saturation hypotheses
because the current graph has no deploy/commit events or metrics to support them.

Prior weight is a recency-weighted evidence count where "recency" is ingestion
time (the only honest time axis available). It is labelled as such via
``prior_basis`` and is deliberately not presented as a probability.
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.core.database import rows
from app.graph.base import GraphEvidence, GraphStore
from app.ingestion.extractors import extract_services

# UPPER_SNAKE_CASE tokens with at least one underscore — e.g. DATABASE_URL,
# KAFKA_BROKERS. The underscore requirement keeps out bare acronyms (URL, API).
ENV_TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b")
ERROR_MARKERS = (
    "fail",
    "error",
    "timeout",
    "refused",
    "unreachable",
    "exception",
    "missing",
    "crash",
    "root cause",
    "caused by",
)
MAX_HYPOTHESES = 4
PRIOR_BASIS = "ingestion_recency_weighted_evidence_count"


def extract_hypotheses(
    graph: GraphStore,
    project_id: str,
    service_name: str,
    evidence: list[GraphEvidence],
) -> list[dict[str, Any]]:
    """Return up to MAX_HYPOTHESES candidate causes for a service-down incident.

    Empty list when there is no service in scope or no usable evidence.
    """
    target = (service_name or "").lower()
    if not target or not evidence:
        return []

    recency = _recency_factors(project_id)
    service_ids = {node.get("id") for node in graph.list_nodes(project_id, "Service", 500)}
    hypotheses: list[dict[str, Any]] = []

    upstream = _upstream_dependency(graph, project_id, target, evidence, service_ids, recency)
    if upstream:
        hypotheses.append(upstream)

    config = _config_mismatch(graph, project_id, target, evidence, recency)
    if config:
        hypotheses.append(config)

    signature = _error_signature(evidence, recency)
    if signature:
        hypotheses.append(signature)

    hypotheses.sort(key=lambda item: (item["weight"], item["evidence_count"]), reverse=True)
    return hypotheses[:MAX_HYPOTHESES]


def _upstream_dependency(
    graph: GraphStore,
    project_id: str,
    target: str,
    evidence: list[GraphEvidence],
    service_ids: set[Any],
    recency: dict[str, float],
) -> dict[str, Any] | None:
    """A dependency of the target is implicated by error-co-occurring evidence."""
    declared: set[str] = set()
    try:
        for edge in graph.list_edges(project_id, "SERVICE_DEPENDS_ON_SERVICE", limit=500):
            if edge.get("from_id") == f"{project_id}:{target}":
                name = str(edge.get("to_id", "")).split(":")[-1].lower()
                if name and name != target:
                    declared.add(name)
    except Exception:
        pass

    support: dict[str, GraphEvidence] = {}
    deps: dict[str, int] = defaultdict(int)
    for item in evidence:
        if not _has_error(item):
            continue
        mentioned = {value.lower() for value in extract_services(item.text)}
        mentioned -= {target}
        # A declared dependency named anywhere in this error-bearing chunk also counts.
        mentioned |= {dep for dep in declared if dep in item.text.lower()}
        for dep in mentioned:
            deps[dep] += 1
            support[item.chunk_id] = item
    if not support:
        return None

    signals = sorted(deps, key=lambda dep: deps[dep], reverse=True)[:4]
    node_ids = [f"{project_id}:{dep}" for dep in signals if f"{project_id}:{dep}" in service_ids]
    listed = ", ".join(signals)
    return _hypothesis(
        hypothesis_id="upstream_dependency_failure",
        category="upstream_dependency",
        label=f"Upstream dependency failure ({listed})",
        signals=signals,
        rationale=(
            f"{target} failures co-occur in retrieved evidence with errors that reference "
            f"dependency service(s): {listed}."
        ),
        support=list(support.values()),
        extra_node_ids=node_ids,
        recency=recency,
    )


def _config_mismatch(
    graph: GraphStore,
    project_id: str,
    target: str,
    evidence: list[GraphEvidence],
    recency: dict[str, float],
) -> dict[str, Any] | None:
    """Configuration / environment variable named in error-bearing evidence."""
    declared: set[str] = set()
    try:
        for edge in graph.list_edges(project_id, "SERVICE_USES_ENV_VAR", limit=500):
            if edge.get("from_id") == f"{project_id}:{target}":
                declared.add(str(edge.get("to_id", "")).split(":")[-1])
    except Exception:
        pass

    support: dict[str, GraphEvidence] = {}
    tokens: dict[str, int] = defaultdict(int)
    for item in evidence:
        if not _has_error(item):
            continue
        found = set(ENV_TOKEN_RE.findall(item.text))
        found |= {name for name in declared if name and name in item.text}
        for token in found:
            tokens[token] += 1
            support[item.chunk_id] = item
    if not support:
        return None

    signals = sorted(tokens, key=lambda token: tokens[token], reverse=True)[:4]
    node_ids = [f"env:{project_id}:{token}" for token in signals if token in declared]
    listed = ", ".join(signals)
    return _hypothesis(
        hypothesis_id="configuration_or_env_mismatch",
        category="configuration",
        label=f"Configuration / environment mismatch ({listed})",
        signals=signals,
        rationale=(
            f"Error-bearing evidence for {target} names configuration / environment "
            f"value(s): {listed}."
        ),
        support=list(support.values()),
        extra_node_ids=node_ids,
        recency=recency,
    )


def _error_signature(
    evidence: list[GraphEvidence], recency: dict[str, float]
) -> dict[str, Any] | None:
    """A recurring error pattern itself, independent of attributed cause."""
    support: dict[str, GraphEvidence] = {}
    patterns: list[str] = []
    for item in evidence:
        errors = _errors_in(item)
        if errors:
            support[item.chunk_id] = item
            patterns.extend(errors)
    if not support:
        return None

    # Pick the longest distinct error line as the most specific signature.
    best = max(dict.fromkeys(patterns), key=len)
    signal = best.strip()[:140]
    return _hypothesis(
        hypothesis_id="error_pattern_signature",
        category="error_signature",
        label=f"Recurring error signature: {signal}",
        signals=[signal],
        rationale="Retrieved evidence repeats an error pattern but does not attribute a cause.",
        support=list(support.values()),
        extra_node_ids=[],
        recency=recency,
    )


def _hypothesis(
    hypothesis_id: str,
    category: str,
    label: str,
    signals: list[str],
    rationale: str,
    support: list[GraphEvidence],
    extra_node_ids: list[str],
    recency: dict[str, float],
) -> dict[str, Any]:
    unique: dict[str, GraphEvidence] = {item.chunk_id: item for item in support}
    chunks = list(unique.values())
    return {
        "id": hypothesis_id,
        "category": category,
        "label": label,
        "signals": signals,
        "rationale": rationale,
        "supporting_evidence": [
            {
                "chunk_id": item.chunk_id,
                "source_type": item.source_type,
                "source_title": item.source_title,
                "source_url": item.source_url,
            }
            for item in chunks
        ],
        "supporting_node_ids": [item.chunk_id for item in chunks] + extra_node_ids,
        "evidence_count": len(chunks),
        "weight": _weight(chunks, recency),
        "prior_basis": PRIOR_BASIS,
    }


def _weight(support: list[GraphEvidence], recency: dict[str, float]) -> float:
    total = 0.0
    for item in support:
        item_id = item.metadata.get("item_id", "")
        total += recency.get(item_id, 1.0)
    return round(total, 3)


def _recency_factors(project_id: str) -> dict[str, float]:
    """Map knowledge_item id -> recency factor in [0.5, 1.0] by ingestion time."""
    records = rows("SELECT id, created_at FROM knowledge_items WHERE project_id=?", (project_id,))
    times: dict[str, datetime] = {}
    for record in records:
        try:
            times[record["id"]] = datetime.fromisoformat(record["created_at"])
        except (ValueError, TypeError):
            continue
    if not times:
        return {}
    newest = max(times.values())
    oldest = min(times.values())
    span = (newest - oldest).total_seconds()
    if span <= 0:
        return {key: 1.0 for key in times}
    return {
        key: round(0.5 + 0.5 * (value - oldest).total_seconds() / span, 3)
        for key, value in times.items()
    }


def _errors_in(item: GraphEvidence) -> list[str]:
    signals = item.metadata.get("signals", {})
    return [str(line) for line in signals.get("errors", []) if str(line).strip()]


def _has_error(item: GraphEvidence) -> bool:
    if _errors_in(item):
        return True
    lowered = item.text.lower()
    return any(marker in lowered for marker in ERROR_MARKERS)
