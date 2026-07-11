"""Turn raw retrieval-trace edges into readable graph paths.

Input is the edge list produced by `GraphStore.get_retrieval_trace` (chunk →
relationship → target). Output is a de-duplicated list of human-readable
path strings plus per-chunk groupings, so the UI and the ask response can
show *why* a chunk was connected instead of a bare edge table.
"""

from __future__ import annotations

from typing import Any


def _label(node_id: Any) -> str:
    text = str(node_id)
    # ids look like "chunk_ab12", "prj_x:reddit_service", "file:prj_x:docker-compose.yml"
    if ":" in text:
        return text.split(":")[-1] or text
    return text


def explain_paths(trace_edges: list[dict[str, Any]], limit: int = 12) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for edge in trace_edges:
        chunk = _label(edge.get("chunk_id") or edge.get("from_id") or "")
        relationship = str(edge.get("relationship", "RELATED_TO"))
        target = _label(edge.get("target_id") or edge.get("to_id") or "")
        if not chunk or not target:
            continue
        path = f"{chunk} —{relationship}→ {target}"
        if path in seen:
            continue
        seen.add(path)
        paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def group_by_target(trace_edges: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group supporting chunks by the graph entity they connect to."""
    grouped: dict[str, list[str]] = {}
    for edge in trace_edges:
        target = _label(edge.get("target_id") or edge.get("to_id") or "")
        chunk = _label(edge.get("chunk_id") or edge.get("from_id") or "")
        if not target or not chunk:
            continue
        grouped.setdefault(target, [])
        if chunk not in grouped[target]:
            grouped[target].append(chunk)
    return grouped
