"""Change-to-incident correlation.

Given a failing service or failure query, rank recently ingested change
evidence (pull requests, issues, CI/workflow files) by overlap with the
failure evidence: shared services, shared environment-variable tokens,
shared file paths, and shared error tokens. The suspect list is built only
from evidence that was actually ingested; recency is ingestion order unless
the source carries its own timestamp metadata, and the basis is labeled.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.database import rows
from app.graph.base import GraphEvidence

CHANGE_SOURCE_TYPES = ("pull_request", "github_issue")
ENV_TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b")
PATH_RE = re.compile(
    r"\b([\w.-]+/[\w./-]+\.[A-Za-z]{1,10}|[\w.-]+\.(?:yml|yaml|py|ts|js|json|toml|conf|env|sh|tf))\b"
)
ERROR_TOKEN_RE = re.compile(
    r"(?i)\b(timeout|refused|unreachable|exception|traceback|panic|oom|5\d\d)\b"
)


def _tokens(text: str) -> dict[str, set[str]]:
    return {
        "env": set(ENV_TOKEN_RE.findall(text)),
        "paths": {value.lower() for value in PATH_RE.findall(text)},
        "errors": {value.lower() for value in ERROR_TOKEN_RE.findall(text)},
    }


def correlate_changes(
    project_id: str,
    failure_evidence: list[GraphEvidence],
    service_name: str | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    """Rank recent change items against the retrieved failure evidence."""
    failure_text = "\n".join(item.text for item in failure_evidence[:8])
    failure_tokens = _tokens(failure_text)
    failure_services = {
        str(name).lower() for item in failure_evidence[:8] for name in item.service_names
    }
    if service_name:
        failure_services.add(service_name.lower())

    if not failure_evidence:
        return {
            "project_id": project_id,
            "suspects": [],
            "reason": "No failure evidence was retrieved, so no change can be correlated.",
            "recency_basis": "ingestion_order",
        }

    placeholders = ",".join("?" for _ in CHANGE_SOURCE_TYPES)
    changes = rows(
        f"SELECT id, source_type, source_title, source_url, content, metadata_json, created_at "
        f"FROM knowledge_items WHERE project_id=? AND source_type IN ({placeholders}) "
        "ORDER BY created_at DESC LIMIT 100",
        (project_id, *CHANGE_SOURCE_TYPES),
    )
    suspects: list[dict[str, Any]] = []
    for rank_from_newest, change in enumerate(changes):
        metadata = json.loads(change["metadata_json"] or "{}")
        change_tokens = _tokens(change["content"])
        change_services = {str(value).lower() for value in metadata.get("services", [])}

        shared_services = sorted(change_services & failure_services)
        shared_env = sorted(change_tokens["env"] & failure_tokens["env"])
        shared_paths = sorted(change_tokens["paths"] & failure_tokens["paths"])
        shared_errors = sorted(change_tokens["errors"] & failure_tokens["errors"])

        score = (
            3.0 * len(shared_services)
            + 2.5 * len(shared_env)
            + 2.0 * len(shared_paths)
            + 1.0 * len(shared_errors)
        )
        if score <= 0:
            continue
        # Newer ingestions get a mild boost; basis is ingestion order.
        score += max(0.0, 1.0 - rank_from_newest / 25.0)

        reasons = []
        if shared_services:
            reasons.append(f"touches service(s) {', '.join(shared_services)}")
        if shared_env:
            reasons.append(f"references env var(s) {', '.join(shared_env[:4])}")
        if shared_paths:
            reasons.append(f"references file(s) {', '.join(shared_paths[:4])}")
        if shared_errors:
            reasons.append(f"mentions the same error term(s) {', '.join(shared_errors[:4])}")
        suspects.append(
            {
                "item_id": change["id"],
                "source_type": change["source_type"],
                "title": change["source_title"],
                "url": change["source_url"],
                "ingested_at": change["created_at"],
                "score": round(score, 2),
                "shared_services": shared_services,
                "shared_env_vars": shared_env,
                "shared_files": shared_paths,
                "reason": (
                    f"{change['source_title']} is suspicious because it "
                    + " and ".join(reasons)
                    + " that also appear in the failure evidence."
                ),
            }
        )
    suspects.sort(key=lambda item: item["score"], reverse=True)
    return {
        "project_id": project_id,
        "service_name": service_name,
        "changes_considered": len(changes),
        "suspects": suspects[:limit],
        "recency_basis": "ingestion_order",
        "reason": (
            "No ingested pull request or issue shares services, env vars, files, or error terms "
            "with the failure evidence."
            if not suspects
            else f"Ranked {len(suspects)} candidate change(s) by evidence overlap."
        ),
    }
