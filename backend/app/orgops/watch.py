"""Standing watches: the same organizational checks, run without being asked.

Asking "are we ready" is useful once. The situation this product is actually
about — a decision recorded in one space that nobody propagated to the space
tracking it — appears at a moment nobody is looking. A watch runs the read tools
on an interval, and anything it finds arrives as a finding with, where a fix is
unambiguous, a plan already drafted and waiting for a person.

The autonomy is in the noticing. Nothing a watch produces is applied on its own.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.database import connect, new_id, row, rows, utcnow

logger = logging.getLogger(__name__)

CHECKS = ("blockers", "conflicts", "stale")
MIN_INTERVAL_SECONDS = 60


def _fingerprint(*parts: str) -> str:
    return hashlib.sha256("::".join(parts).encode()).hexdigest()[:32]


def _decode(value: Any, fallback: Any) -> Any:
    try:
        return json.loads(value) if value else fallback
    except (TypeError, ValueError):
        return fallback


class WatchService:
    """Create, run, and report on standing organizational watches."""

    def __init__(self, orgops: Any):
        self.orgops = orgops

    # ------------------------------------------------------------- lifecycle

    def create(
        self,
        workspace_id: str,
        user_id: str,
        name: str,
        space_ids: list[str],
        checks: list[str] | None = None,
        interval_seconds: int = 900,
    ) -> dict:
        selected = [check for check in (checks or list(CHECKS)) if check in CHECKS]
        if not selected:
            raise ValueError(f"checks must be a subset of {list(CHECKS)}")
        if not space_ids:
            raise ValueError("A watch needs at least one space")
        watch_id, now = new_id("watch"), utcnow()
        with connect() as conn:
            conn.execute(
                "INSERT INTO org_watches (id,workspace_id,name,space_ids_json,checks_json,"
                "interval_seconds,status,created_by,last_run_at,last_error,runs,created_at,"
                "updated_at) VALUES (?,?,?,?,?,?,'active',?,NULL,'',0,?,?)",
                (
                    watch_id,
                    workspace_id,
                    name.strip() or "Organizational watch",
                    json.dumps(space_ids),
                    json.dumps(selected),
                    max(MIN_INTERVAL_SECONDS, int(interval_seconds)),
                    user_id,
                    now,
                    now,
                ),
            )
        return self.get(watch_id)

    def get(self, watch_id: str) -> dict:
        record = row("SELECT * FROM org_watches WHERE id=?", (watch_id,))
        if not record:
            raise LookupError("Watch not found")
        return self.public(record)

    def public(self, record: dict) -> dict:
        findings = rows(
            "SELECT * FROM org_watch_findings WHERE watch_id=? ORDER BY created_at DESC LIMIT 20",
            (record["id"],),
        )
        return {
            "id": record["id"],
            "name": record["name"],
            "space_ids": _decode(record.get("space_ids_json"), []),
            "checks": _decode(record.get("checks_json"), []),
            "interval_seconds": record.get("interval_seconds", 900),
            "status": record.get("status", "active"),
            "runs": record.get("runs", 0),
            "last_run_at": record.get("last_run_at"),
            "last_error": record.get("last_error", ""),
            "open_findings": len([item for item in findings if item["status"] == "open"]),
            "findings": [
                {
                    "id": item["id"],
                    "kind": item["kind"],
                    "headline": item["headline"],
                    "detail": item.get("detail", ""),
                    "plan_id": item.get("plan_id", ""),
                    "status": item.get("status", "open"),
                    "created_at": item.get("created_at"),
                    "payload": _decode(item.get("payload_json"), {}),
                }
                for item in findings
            ],
            "created_at": record.get("created_at"),
        }

    def list(self, workspace_id: str) -> list[dict]:
        return [
            self.public(record)
            for record in rows(
                "SELECT * FROM org_watches WHERE workspace_id=? ORDER BY created_at DESC LIMIT 25",
                (workspace_id,),
            )
        ]

    def delete(self, watch_id: str, workspace_id: str) -> None:
        with connect() as conn:
            conn.execute(
                "DELETE FROM org_watches WHERE id=? AND workspace_id=?", (watch_id, workspace_id)
            )

    def resolve_finding(self, finding_id: str, workspace_id: str) -> dict:
        with connect() as conn:
            conn.execute(
                "UPDATE org_watch_findings SET status='resolved',resolved_at=? "
                "WHERE id=? AND workspace_id=?",
                (utcnow(), finding_id, workspace_id),
            )
        record = row("SELECT * FROM org_watch_findings WHERE id=?", (finding_id,))
        if not record:
            raise LookupError("Finding not found")
        return {"id": record["id"], "status": record["status"]}

    # ------------------------------------------------------------------- run

    def run(self, watch_id: str, user_id: str = "") -> dict:
        record = row("SELECT * FROM org_watches WHERE id=?", (watch_id,))
        if not record:
            raise LookupError("Watch not found")
        space_ids = _decode(record.get("space_ids_json"), [])
        checks = _decode(record.get("checks_json"), [])
        workspace_id = record["workspace_id"]
        found: list[dict] = []
        error = ""

        try:
            if "blockers" in checks:
                found.extend(self._blocker_findings(space_ids))
            if "conflicts" in checks:
                found.extend(self._conflict_findings(space_ids))
            if "stale" in checks:
                found.extend(self._stale_findings(space_ids))
        except Exception as exc:  # a broken watch must not take the worker down
            logger.exception("Watch %s failed", watch_id)
            error = str(exc)

        recorded = 0
        now = utcnow()
        author = user_id or record["created_by"]
        for finding in found:
            finding_id = new_id("find")
            with connect() as conn:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO org_watch_findings "
                    "(id,watch_id,workspace_id,kind,headline,detail,payload_json,fingerprint,"
                    "plan_id,status,created_at) VALUES (?,?,?,?,?,?,?,?,'','open',?)",
                    (
                        finding_id,
                        watch_id,
                        workspace_id,
                        finding["kind"],
                        finding["headline"],
                        finding.get("detail", ""),
                        json.dumps(finding.get("payload", {})),
                        finding["fingerprint"],
                        now,
                    ),
                )
                is_new = cursor.rowcount == 1
            recorded += 1 if is_new else 0
            # Only a genuinely new finding drafts a plan. Drafting on every pass
            # would file the same fix every few minutes and bury the queue it is
            # supposed to make legible.
            if is_new and finding.get("resolution"):
                plan_id = self._draft_plan(finding, workspace_id, author)
                if plan_id:
                    with connect() as conn:
                        conn.execute(
                            "UPDATE org_watch_findings SET plan_id=? WHERE id=?",
                            (plan_id, finding_id),
                        )

        with connect() as conn:
            conn.execute(
                "UPDATE org_watches SET last_run_at=?,last_error=?,runs=runs+1,updated_at=? "
                "WHERE id=?",
                (now, error, now, watch_id),
            )
        return {**self.get(watch_id), "new_findings": recorded, "checked": len(found)}

    def due(self) -> list[str]:
        """Watches whose interval has elapsed."""
        now = datetime.now(UTC)
        ready: list[str] = []
        for record in rows("SELECT * FROM org_watches WHERE status='active'"):
            last = record.get("last_run_at")
            if not last:
                ready.append(record["id"])
                continue
            try:
                stamp = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            except ValueError:
                ready.append(record["id"])
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=UTC)
            if now - stamp >= timedelta(seconds=record.get("interval_seconds", 900)):
                ready.append(record["id"])
        return ready

    def run_due(self) -> int:
        ran = 0
        for watch_id in self.due():
            try:
                self.run(watch_id)
                ran += 1
            except Exception:
                logger.exception("Scheduled watch %s failed", watch_id)
        return ran

    # -------------------------------------------------------------- checks

    def _blocker_findings(self, space_ids: list[str]) -> list[dict]:
        result = self.orgops.find_blockers(space_ids)
        findings = []
        for blocker in result["blockers"]:
            task = blocker["task"]
            findings.append(
                {
                    "kind": "blocker",
                    "headline": f"{task['title']} is holding {len(blocker['blocks'])} other item(s)",
                    "detail": (
                        f"{task['space_name']} · owner {task['owner'] or 'unassigned'} · "
                        f"{blocker['severity']}"
                    ),
                    # The status is part of the identity: the same task blocking
                    # again after it was closed is genuinely new information.
                    "fingerprint": _fingerprint("blocker", task["id"], task["status"]),
                    "payload": blocker,
                }
            )
        return findings

    def _conflict_findings(self, space_ids: list[str]) -> list[dict]:
        """Look, and only look. The fix is drafted later, and only if new."""
        result = self.orgops.find_conflicts(space_ids)
        findings = []
        for conflict in result["conflicts"]:
            task = conflict["task"]
            source = conflict["source"]
            findings.append(
                {
                    "kind": "conflict",
                    "headline": (
                        f"“{task['title']}” is {conflict['tracked_state']}, but "
                        f"{source['space_name']} already settled it"
                    ),
                    "detail": source["title"],
                    "fingerprint": _fingerprint("conflict", task["id"], source["id"]),
                    "payload": conflict,
                    "resolution": {
                        "space_id": task["space_id"],
                        "summary": f"Reconcile “{task['title']}” with {source['space_name']}",
                        "operations": [conflict["resolution"]],
                    },
                }
            )
        return findings

    def _draft_plan(self, finding: dict, workspace_id: str, user_id: str) -> str:
        """A contradiction has one unambiguous fix, so the watch writes it down.

        Writing it down is not doing it: the plan lands in the approval queue.
        """
        resolution = finding["resolution"]
        try:
            plan = self.orgops.propose_plan(
                workspace_id,
                user_id,
                resolution["space_id"],
                resolution["summary"],
                resolution["operations"],
                origin="watch",
            )
            return plan["id"]
        except Exception:
            logger.exception("Could not draft a reconciliation plan")
            return ""

    def _stale_findings(self, space_ids: list[str]) -> list[dict]:
        result = self.orgops.find_stale_information(space_ids, max_age_days=120)
        findings = []
        for entry in result["stale"][:5]:
            findings.append(
                {
                    "kind": "stale",
                    "headline": f"“{entry['title']}” has not been confirmed in {entry['age_days']} days",
                    "detail": f"{entry['space_name']} · {entry['type']}",
                    "fingerprint": _fingerprint("stale", entry["id"]),
                    "payload": entry,
                }
            )
        return findings
