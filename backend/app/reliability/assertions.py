"""Lifecycle state for evidence-backed operational assertions.

The graph holds assertion relationships; SQLite holds mutable review state and
the audit log. Assertions are deliberately claims with bounded provenance, not
document chunks or model-generated facts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from app.audit import AuditService
from app.core.config import settings
from app.core.database import connect, new_id, row, rows, utcnow
from app.graph.base import GraphStore

ASSERTION_STATUSES = {
    "proposed",
    "verified",
    "possibly_stale",
    "stale",
    "contradicted",
    "superseded",
}


class OperationalAssertionService:
    def __init__(self, graph: GraphStore, audit: AuditService | None = None):
        self.graph = graph
        self.audit = audit or AuditService()

    def create(self, project_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = utcnow()
        assertion_id = payload.get("id") or new_id("assert")
        status = payload.get("status", "proposed")
        if status not in ASSERTION_STATUSES:
            raise ValueError("Unsupported assertion status")
        evidence = list(payload.get("evidence") or [])
        record = {
            "id": assertion_id,
            "project_id": project_id,
            "title": payload["title"],
            "claim": payload["claim"],
            "subject_type": payload.get("subject_type", "runbook_step"),
            "subject_id": payload.get("subject_id", ""),
            "environment_scope": payload.get("environment_scope", "unknown"),
            "status": status,
            "confidence": float(payload.get("confidence", 0.0)),
            "trust_score": float(payload.get("trust_score", 0.0)),
            "created_at": payload.get("created_at", now),
            "updated_at": now,
            "last_verified_at": payload.get("last_verified_at"),
            "valid_from": payload.get("valid_from"),
            "valid_to": payload.get("valid_to"),
            "source_version": payload.get("source_version", ""),
            "commit_sha": payload.get("commit_sha", ""),
            "source_updated_at": payload.get("source_updated_at"),
            "verification_owner": payload.get("verification_owner", "owner unknown"),
            "verification_reason": payload.get("verification_reason", ""),
            "evidence": evidence,
            "affected_runbook_ids": list(payload.get("affected_runbook_ids") or []),
            "affected_runbook_step_ids": list(payload.get("affected_runbook_step_ids") or []),
            "approval_requirement": payload.get("approval_requirement", "human_review_required"),
            "policy_status": payload.get("policy_status", "unverified"),
        }
        with connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO operational_assertions
                (id,project_id,title,claim,subject_type,subject_id,environment_scope,status,confidence,trust_score,
                 created_at,updated_at,last_verified_at,valid_from,valid_to,source_version,commit_sha,source_updated_at,
                 verification_owner,verification_reason,evidence_json,affected_runbook_ids_json,
                 affected_runbook_step_ids_json,approval_requirement,policy_status)
                VALUES (:id,:project_id,:title,:claim,:subject_type,:subject_id,:environment_scope,:status,:confidence,:trust_score,
                 :created_at,:updated_at,:last_verified_at,:valid_from,:valid_to,:source_version,:commit_sha,:source_updated_at,
                 :verification_owner,:verification_reason,:evidence,:affected_runbook_ids,:affected_runbook_step_ids,
                 :approval_requirement,:policy_status)""",
                {
                    **record,
                    "evidence": json.dumps(evidence),
                    "affected_runbook_ids": json.dumps(record["affected_runbook_ids"]),
                    "affected_runbook_step_ids": json.dumps(record["affected_runbook_step_ids"]),
                },
            )
        self._sync_graph(record)
        self.audit.record(
            "assertion.created",
            f"Created assertion: {record['title']}",
            project_id,
            payload={"assertion_id": assertion_id, "status": status},
        )
        return record

    def ensure_runbook_assertions(
        self, project_id: str, runbook: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Create one idempotent, evidence-linked claim per extracted step."""
        payload = runbook["payload"]
        created = []
        sources = list(payload.get("sources") or [])
        primary_source = sources[0] if sources else {}
        owner, owner_source = self._suggest_owner(project_id, sources)
        for step in payload.get("steps", []):
            step_id = f"{runbook['id']}:{step['id']}"
            existing = row(
                "SELECT * FROM operational_assertions WHERE project_id=? AND subject_type='runbook_step' AND subject_id=?",
                (project_id, step_id),
            )
            if existing:
                continue
            environment = (
                "production" if step.get("action_type") == "production_change" else "unknown"
            )
            created.append(
                self.create(
                    project_id,
                    {
                        "title": f"{payload.get('name', 'Runbook')} — {step['id']}",
                        "claim": step.get("description", ""),
                        "subject_type": "runbook_step",
                        "subject_id": step_id,
                        "environment_scope": environment,
                        "status": "proposed",
                        "confidence": payload.get("confidence", 0.0),
                        "trust_score": (payload.get("trust_score") or {}).get("score", 0.0),
                        "source_version": primary_source.get(
                            "source_version", str(payload.get("version", 1))
                        ),
                        "commit_sha": primary_source.get("commit_sha", ""),
                        "source_updated_at": primary_source.get("source_updated_at", ""),
                        "verification_owner": owner,
                        "verification_reason": f"Owner auto-suggested from {owner_source}",
                        "evidence": [
                            {
                                "source_item_id": source.get("item_id", ""),
                                "snippet": source.get("snippet", ""),
                                "provenance": source.get("url", ""),
                                "graph_paths": payload.get("graph_trace", []),
                            }
                            for source in sources
                            if source.get("item_id")
                        ],
                        "affected_runbook_ids": [runbook["id"]],
                        "affected_runbook_step_ids": [step_id],
                        "approval_requirement": (
                            "admin_review_required"
                            if environment == "production"
                            else "human_review_required"
                        ),
                    },
                )
            )
        return created

    def list(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        self.assign_suggested_owners(project_id)
        self.auto_verify_undisputed(project_id)
        sql = "SELECT * FROM operational_assertions WHERE project_id=?"
        params: tuple[Any, ...] = (project_id,)
        if status:
            sql += " AND status=?"
            params += (status,)
        records = [self._decode(item) for item in rows(sql + " ORDER BY updated_at DESC", params)]
        # Runbook extraction is replaceable. If a prior extraction was removed
        # or failed, its step assertions must not remain visible as live policy.
        valid_runbook_ids = {
            item["id"] for item in rows("SELECT id FROM runbooks WHERE project_id=?", (project_id,))
        }
        return [
            record
            for record in records
            if record.get("subject_type") != "runbook_step"
            or bool(set(record.get("affected_runbook_ids") or []).intersection(valid_runbook_ids))
        ]

    def assign_suggested_owners(self, project_id: str) -> dict[str, Any]:
        updated: list[str] = []
        for raw in rows(
            "SELECT * FROM operational_assertions WHERE project_id=? AND "
            "(verification_owner='' OR lower(verification_owner)='owner unknown')",
            (project_id,),
        ):
            record = self._decode(raw)
            owner, source = self._suggest_owner(project_id, record.get("evidence") or [])
            with connect() as conn:
                conn.execute(
                    "UPDATE operational_assertions SET verification_owner=?, "
                    "verification_reason=?, updated_at=? WHERE id=? AND project_id=?",
                    (
                        owner,
                        f"Owner auto-suggested from {source}",
                        utcnow(),
                        record["id"],
                        project_id,
                    ),
                )
            refreshed = self.get(record["id"], project_id)
            if refreshed:
                self._sync_graph(refreshed)
                updated.append(record["id"])
        if updated:
            self.audit.record(
                "assertion.owners_suggested",
                f"Suggested owners for {len(updated)} assertions",
                project_id,
                payload={"assertion_ids": updated},
            )
        return {"updated": len(updated), "assertion_ids": updated}

    def auto_verify_undisputed(self, project_id: str) -> dict[str, Any]:
        if not settings.assertion_auto_verify_enabled:
            return {"enabled": False, "verified": 0}
        cutoff = datetime.now(UTC) - timedelta(days=max(1, settings.assertion_auto_verify_days))
        verified: list[str] = []
        for raw in rows(
            "SELECT * FROM operational_assertions WHERE project_id=? AND status='proposed' "
            "AND policy_status='unverified'",
            (project_id,),
        ):
            record = self._decode(raw)
            try:
                created = datetime.fromisoformat(str(record["created_at"]).replace("Z", "+00:00"))
                if not created.tzinfo:
                    created = created.replace(tzinfo=UTC)
            except (TypeError, ValueError):
                continue
            if created > cutoff or not record.get("commit_sha"):
                continue
            if record.get("verification_owner") in {"", "owner unknown"}:
                continue
            evidence_ids = [item.get("source_item_id") for item in record.get("evidence") or []]
            current_versions = []
            for item_id in evidence_ids:
                item = row("SELECT metadata_json FROM knowledge_items WHERE id=?", (item_id,))
                if not item:
                    continue
                try:
                    current_versions.append(json.loads(item["metadata_json"] or "{}"))
                except json.JSONDecodeError:
                    continue
            if not current_versions or any(
                value.get("commit_sha") != record["commit_sha"] for value in current_versions
            ):
                continue
            self.transition(
                record["id"],
                "verify",
                "Runbook stability policy",
                f"Auto-verified after {settings.assertion_auto_verify_days} days with unchanged commit evidence.",
                project_id,
            )
            verified.append(record["id"])
        return {"enabled": True, "verified": len(verified), "assertion_ids": verified}

    def bulk_review(
        self,
        project_id: str,
        assertion_ids: list[str],
        action: str,
        actor: str,
        reason: str,
        owner: str = "",
    ) -> dict[str, Any]:
        if not assertion_ids:
            raise ValueError("Select at least one assertion")
        results: list[dict[str, Any]] = []
        for assertion_id in dict.fromkeys(assertion_ids):
            record = self.get(assertion_id, project_id)
            if not record:
                raise ValueError(f"Assertion {assertion_id} is not in this project")
            if owner.strip():
                with connect() as conn:
                    conn.execute(
                        "UPDATE operational_assertions SET verification_owner=?, updated_at=? "
                        "WHERE id=? AND project_id=?",
                        (owner.strip(), utcnow(), assertion_id, project_id),
                    )
            results.append(self.transition(assertion_id, action, actor, reason, project_id))
        return {"reviewed": len(results), "action": action, "assertions": results}

    def _suggest_owner(self, project_id: str, evidence: list[dict[str, Any]]) -> tuple[str, str]:
        for item in evidence:
            item_id = item.get("source_item_id")
            if not item_id:
                continue
            source = row("SELECT metadata_json FROM knowledge_items WHERE id=?", (item_id,))
            if not source:
                continue
            try:
                metadata = json.loads(source["metadata_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if metadata.get("owner"):
                return str(metadata["owner"]), str(metadata.get("owner_source") or "source owner")
            if metadata.get("latest_commit_author"):
                return str(metadata["latest_commit_author"]), "last committer"
        metadata_items = rows(
            "SELECT metadata_json FROM knowledge_items WHERE project_id=? "
            "AND source_type='repository_metadata' ORDER BY created_at DESC",
            (project_id,),
        )
        for item in metadata_items:
            try:
                metadata = json.loads(item["metadata_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if metadata.get("latest_commit_author"):
                return str(metadata["latest_commit_author"]), "repository last committer"
            if metadata.get("owner"):
                return str(metadata["owner"]), "repository owner"
        project = row("SELECT repository FROM projects WHERE id=?", (project_id,)) or {}
        repository = str(project.get("repository") or "")
        if "github.com/" in repository:
            slug = repository.split("github.com/", 1)[1].strip("/").removesuffix(".git")
            if "/" in slug:
                return slug.split("/", 1)[0], "repository namespace"
        return "Workspace reliability team", "workspace reliability fallback"

    def get(self, assertion_id: str, project_id: str | None = None) -> dict[str, Any] | None:
        sql = "SELECT * FROM operational_assertions WHERE id=?"
        params: tuple[Any, ...] = (assertion_id,)
        if project_id:
            sql += " AND project_id=?"
            params += (project_id,)
        record = row(sql, params)
        return self._decode(record) if record else None

    def transition(
        self,
        assertion_id: str,
        action: str,
        actor: str,
        reason: str,
        project_id: str | None = None,
        superseded_by: str = "",
    ) -> dict[str, Any]:
        record = self.get(assertion_id, project_id)
        if not record:
            raise ValueError("Assertion not found")
        if action in {"mark_stale", "supersede", "dismiss"} and not reason.strip():
            raise ValueError("A rationale is required for this assertion decision")
        previous = record["status"]
        now = utcnow()
        if action == "verify":
            status, policy_status, verified_at = "verified", "trusted", now
        elif action == "mark_stale":
            status, policy_status, verified_at = (
                "stale",
                "blocked_pending_review",
                record.get("last_verified_at"),
            )
        elif action == "supersede":
            status, policy_status, verified_at = (
                "superseded",
                "superseded",
                record.get("last_verified_at"),
            )
        elif action == "dismiss":
            # Dismissal records a reviewer decision; it never turns an unresolved claim into trusted evidence.
            status, policy_status, verified_at = (
                previous,
                "dismissed",
                record.get("last_verified_at"),
            )
        else:
            raise ValueError("Unsupported assertion decision")
        with connect() as conn:
            conn.execute(
                """UPDATE operational_assertions SET status=?, policy_status=?, verification_reason=?,
                last_verified_at=?, valid_to=?, updated_at=? WHERE id=? AND project_id=?""",
                (
                    status,
                    policy_status,
                    reason,
                    verified_at,
                    now if action == "supersede" else record.get("valid_to"),
                    now,
                    assertion_id,
                    record["project_id"],
                ),
            )
        updated = self.get(assertion_id, record["project_id"])
        assert updated
        self._sync_graph(updated)
        self.audit.record(
            f"assertion.{action}",
            f"{action.replace('_', ' ').title()} assertion: {record['title']}",
            record["project_id"],
            actor,
            {
                "assertion_id": assertion_id,
                "previous_status": previous,
                "new_status": status,
                "reason": reason,
                "superseded_by": superseded_by,
            },
        )
        return updated

    def applicable_to_step(
        self, project_id: str, runbook_id: str, step_id: str
    ) -> list[dict[str, Any]]:
        step_vertex_id = f"{runbook_id}:{step_id}"
        records = self.list(project_id)
        return [
            item
            for item in records
            if step_vertex_id in item["affected_runbook_step_ids"]
            or runbook_id in item["affected_runbook_ids"]
        ]

    def flag_possibly_stale(self, assertion_id: str, reason: str) -> dict[str, Any]:
        """A connected change downgrades a verified claim; it does not prove it false."""
        record = self.get(assertion_id)
        if not record or record["status"] != "verified":
            return record or {}
        now = utcnow()
        with connect() as conn:
            conn.execute(
                "UPDATE operational_assertions SET status='possibly_stale', policy_status='review_required', verification_reason=?, updated_at=? WHERE id=?",
                (reason, now, assertion_id),
            )
        updated = self.get(assertion_id, record["project_id"])
        assert updated
        self._sync_graph(updated)
        self.audit.record(
            "assertion.possibly_stale",
            f"Change evidence requires review: {record['title']}",
            record["project_id"],
            payload={
                "assertion_id": assertion_id,
                "previous_status": "verified",
                "new_status": "possibly_stale",
                "reason": reason,
            },
        )
        return updated

    def _sync_graph(self, record: dict[str, Any]) -> None:
        self.graph.upsert_operational_assertion(
            {
                key: value
                for key, value in record.items()
                if key not in {"evidence", "affected_runbook_ids", "affected_runbook_step_ids"}
            }
        )
        subject_type = {
            "service": "Service",
            "file": "File",
            "environment_variable": "EnvironmentVariable",
            "config_key": "ConfigKey",
            "runbook_step": "RunbookStep",
            "command": "Command",
        }.get(record["subject_type"])
        if subject_type and record["subject_id"]:
            self.graph.link(
                "ASSERTION_ABOUT_SUBJECT",
                "OperationalAssertion",
                record["id"],
                subject_type,
                record["subject_id"],
            )
        for runbook_id in record["affected_runbook_ids"]:
            self.graph.link(
                "ASSERTION_AFFECTS_RUNBOOK",
                "OperationalAssertion",
                record["id"],
                "Runbook",
                runbook_id,
            )
        for step_id in record["affected_runbook_step_ids"]:
            self.graph.link(
                "ASSERTION_AFFECTS_RUNBOOK_STEP",
                "OperationalAssertion",
                record["id"],
                "RunbookStep",
                step_id,
            )
        for evidence in record["evidence"]:
            source_id = evidence.get("source_item_id")
            if source_id:
                self.graph.link(
                    "ASSERTION_SUPPORTED_BY",
                    "OperationalAssertion",
                    record["id"],
                    "KnowledgeItem",
                    source_id,
                )

    @staticmethod
    def _decode(record: dict[str, Any]) -> dict[str, Any]:
        result = dict(record)
        for key in ("evidence", "affected_runbook_ids", "affected_runbook_step_ids"):
            result[key] = json.loads(result.pop(f"{key}_json") or "[]")
        return result
