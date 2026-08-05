"""Bounded graph activation shared by the in-memory and ArcadeDB stores.

The traversal is deliberately deterministic. Query terms activate typed
entities, then a breadth-first walk follows knowledge-bearing relationships
until it reaches evidence chunks. It never invents an edge or lets graph
proximity replace source evidence.
"""

from __future__ import annotations

import json
import re
from collections import deque
from dataclasses import dataclass
from typing import Any

from .base import GraphEvidence

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.@/{}/:-]{2,}")
STOP_WORDS = {
    "about",
    "after",
    "before",
    "company",
    "context",
    "does",
    "evidence",
    "explain",
    "from",
    "have",
    "into",
    "memory",
    "project",
    "repository",
    "service",
    "that",
    "their",
    "this",
    "what",
    "when",
    "where",
    "which",
    "with",
}

# Context activation may walk structure, provenance, current-truth, and
# collaboration edges. Execution/approval edges are intentionally excluded.
CONTEXT_RELATIONSHIPS = {
    "ARTIFACT_DERIVED_FROM_MEMORY",
    "BELIEF_CONTRADICTED_BY",
    "BELIEF_SUPPORTED_BY",
    "CHUNK_DERIVED_FROM",
    "CHUNK_DERIVED_FROM_FILE",
    "CHUNK_REFERENCES_SERVICE",
    "CONTEXT_WINDOW_CONTAINS_CHUNK",
    "CONTRADICTS",
    "DECIDED_BY",
    "DEPENDS_ON",
    "DERIVES",
    "DIRECTORY_HAS_FILE",
    "EXTENDS",
    "FILE_DEFINES_CLASS",
    "FILE_DEFINES_ENDPOINT",
    "FILE_DEFINES_FUNCTION",
    "FILE_HAS_CHUNK",
    "FILE_IMPORTS_FILE",
    "FILE_IMPORTS_MODULE",
    "FILE_MENTIONS_SERVICE",
    "FILE_REFERENCES_CONFIG_KEY",
    "FILE_REFERENCES_ENV_VAR",
    "FILE_WRITTEN_IN_LANGUAGE",
    "INVALIDATED_BY",
    "INVALIDATES",
    "ISSUE_MENTIONS_SERVICE",
    "ISSUE_REFERENCES_FILE",
    "MEMORY_DERIVED_FROM_CHUNK",
    "MEMORY_DERIVED_FROM_SOURCE",
    "MENTIONS",
    "OWNED_BY",
    "PACKAGE_HAS_DEPENDENCY",
    "REPO_HAS_WORKFLOW",
    "PR_REFERENCES_ISSUE",
    "PR_TOUCHES_FILE",
    "PROJECT_HAS_REPO",
    "PROJECT_HAS_SERVICE",
    "REPO_HAS_COMMIT",
    "REPO_HAS_DIRECTORY",
    "REPO_HAS_FILE",
    "REPO_HAS_ISSUE",
    "REPO_HAS_PULL_REQUEST",
    "REVISION_SUPERSEDES",
    "SERVICE_DEFINED_IN_FILE",
    "SERVICE_DEPENDS_ON_SERVICE",
    "SERVICE_HAS_DOCKER_CONFIG",
    "SERVICE_USES_ENV_VAR",
    "SLACK_MESSAGE_MENTIONS_SERVICE",
    "SLACK_MESSAGE_REFERENCES_FILE",
    "SOURCE_HAS_REVISION",
    "WORKFLOW_HAS_JOB",
    "JOB_HAS_STEP",
    "SUPPORTS",
    "UPDATES",
    "VALID_FOR",
}

SEED_FIELDS = (
    "id",
    "name",
    "path",
    "filename",
    "route",
    "title",
    "statement",
    "subject",
    "content",
    "claim",
    "current_value",
    "repository",
    "full_name",
    "domain",
    "subdomain",
)


@dataclass(frozen=True)
class TraversalHit:
    chunk_id: str
    seed_id: str
    seed_type: str
    seed_score: float
    hops: int
    path: tuple[dict[str, Any], ...]

    @property
    def score(self) -> float:
        return self.seed_score * 8.0 + max(0, 4 - self.hops) * 3.0


def query_terms(query: str) -> tuple[set[str], set[str]]:
    raw = [value.strip("./:{}-") for value in TOKEN_RE.findall(query)]
    terms = {value.casefold() for value in raw if value and value.casefold() not in STOP_WORDS}
    anchors = {
        value.casefold()
        for value in raw
        if value
        and (
            "_" in value
            or "/" in value
            or "." in value
            or "-" in value
            or any(character.isupper() for character in value[1:])
        )
    }
    return terms, anchors


def find_traversal_hits(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    query: str,
    *,
    max_hops: int,
    limit: int,
) -> list[TraversalHit]:
    max_hops = max(1, min(max_hops, 5))
    terms, anchors = query_terms(query)
    if not terms and not anchors:
        return []

    by_id = {str(node.get("id") or ""): node for node in nodes if str(node.get("id") or "")}
    chunk_ids = {
        node_id
        for node_id, node in by_id.items()
        if str(node.get("node_type") or "") == "KnowledgeChunk"
    }
    seeds: list[tuple[float, str, str]] = []
    for node_id, node in by_id.items():
        node_type = str(node.get("node_type") or "")
        if node_type in {"KnowledgeChunk", "KnowledgeItem", "ContextEnvelope"}:
            continue
        searchable = " ".join(str(node.get(field) or "") for field in SEED_FIELDS).casefold()
        anchor_hits = sum(anchor in searchable for anchor in anchors)
        term_hits = sum(_term_match(term, searchable) for term in terms)
        if not anchor_hits and not term_hits:
            continue
        score = anchor_hits * 4.0 + min(term_hits, 6)
        seeds.append((score, node_id, node_type))
    seeds.sort(key=lambda value: (value[0], value[2], value[1]), reverse=True)
    seeds = seeds[:24]
    if not seeds:
        return []

    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for edge in edges:
        relationship = str(edge.get("relationship") or "")
        if relationship not in CONTEXT_RELATIONSHIPS:
            continue
        from_id = str(edge.get("from_id") or "")
        to_id = str(edge.get("to_id") or "")
        if not from_id or not to_id:
            continue
        forward = {
            "from_id": from_id,
            "to_id": to_id,
            "relationship": relationship,
            "direction": "forward",
        }
        reverse = {
            "from_id": to_id,
            "to_id": from_id,
            "relationship": relationship,
            "direction": "reverse",
        }
        adjacency.setdefault(from_id, []).append((to_id, forward))
        adjacency.setdefault(to_id, []).append((from_id, reverse))

    best: dict[str, TraversalHit] = {}
    for seed_score, seed_id, seed_type in seeds:
        queue = deque([(seed_id, 0, tuple())])
        visited = {seed_id}
        while queue:
            node_id, hops, path = queue.popleft()
            if node_id in chunk_ids and hops:
                hit = TraversalHit(node_id, seed_id, seed_type, seed_score, hops, path)
                current = best.get(node_id)
                if current is None or hit.score > current.score:
                    best[node_id] = hit
                continue
            if hops >= max_hops:
                continue
            for target_id, edge in adjacency.get(node_id, []):
                if target_id in visited or target_id not in by_id:
                    continue
                visited.add(target_id)
                queue.append((target_id, hops + 1, (*path, edge)))

    return sorted(best.values(), key=lambda value: value.score, reverse=True)[:limit]


def evidence_from_hits(
    hits: list[TraversalHit],
    chunks: dict[str, dict[str, Any]],
) -> list[GraphEvidence]:
    output: list[GraphEvidence] = []
    for hit in hits:
        record = chunks.get(hit.chunk_id)
        if not record:
            continue
        metadata = _json_value(record.get("metadata_json"), {})
        confidence = min(
            0.86,
            0.42 + min(0.24, hit.seed_score * 0.035) + max(0.0, 0.12 - hit.hops * 0.025),
        )
        metadata.update(
            {
                "primary_lane": "graph_traversal",
                "retrieval_confidence": round(confidence, 3),
                "graph_seed_id": hit.seed_id,
                "graph_seed_type": hit.seed_type,
                "graph_hops": hit.hops,
                "graph_path_edges": list(hit.path),
                "retrieval_lanes": {"graph_traversal": round(hit.score, 3)},
                "score_components": {"graph_traversal": round(hit.score, 3)},
            }
        )
        services = _json_value(record.get("service_names"), [])
        output.append(
            GraphEvidence(
                chunk_id=hit.chunk_id,
                text=str(record.get("text") or ""),
                source_type=str(record.get("source_type") or "unknown"),
                source_title=str(record.get("source_title") or "Untitled source"),
                source_url=str(record.get("source_url") or ""),
                service_names=list(services or []),
                metadata=metadata,
                score=hit.score,
                graph_paths=[
                    " → ".join(
                        [
                            hit.seed_id,
                            *(f"{edge['relationship']}:{edge['to_id']}" for edge in hit.path),
                        ]
                    )
                ],
            )
        )
    return output


def _term_match(term: str, text: str) -> bool:
    if term in text:
        return True
    return len(term) > 4 and term.endswith("s") and term[:-1] in text


def _json_value(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback
