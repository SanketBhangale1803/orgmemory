"""Runbook drift detection.

A runbook drifts when the knowledge it was extracted from changes underneath
it. Every signal here is derived from state Runbook actually tracks:

- a cited source item no longer exists in the knowledge base
- a source with the same title/type was re-ingested with different content
  after the runbook was last updated
- a service the runbook applies to no longer exists in the project graph
- newer error-bearing evidence about the runbook's services arrived after
  extraction (grounds for review, not proof of staleness)
- current evidence contains cause statements that contradict each other

Statuses: fresh, possibly_stale, stale, conflicting_evidence,
needs_human_review.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from app.audit import AuditService
from app.core.database import connect, new_id, row, rows, utcnow
from app.graph.base import GraphStore
from app.intelligence.trust import detect_contradictions

if TYPE_CHECKING:
    from app.runbooks import RunbookService

STATUS_ORDER = ["fresh", "possibly_stale", "needs_human_review", "conflicting_evidence", "stale"]


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()[:16]


class DriftService:
    def __init__(self, graph: GraphStore, runbooks: RunbookService, hcag, audit=None):
        self.graph = graph
        self.runbooks = runbooks
        self.hcag = hcag
        self.audit = audit or AuditService()

    def check_runbook(self, runbook_id: str, project_id: str | None = None) -> dict[str, Any]:
        record = self.runbooks.get(runbook_id, project_id)
        if not record:
            raise ValueError("Runbook not found")
        project_id = record["project_id"]
        payload = record["payload"]
        signals: list[dict[str, Any]] = []

        signals += self._missing_or_changed_sources(project_id, record, payload)
        signals += self._missing_services(project_id, payload)
        signals += self._newer_error_evidence(project_id, record, payload)
        signals += self._conflicting_evidence(project_id, payload)

        status = self._status(signals, payload.get("confidence", 0.0))
        result = {
            "runbook_id": record["id"],
            "runbook_key": record["runbook_key"],
            "project_id": project_id,
            "drift_status": status,
            "signals": signals,
            "checked_at": utcnow(),
            "sources_checked": len(payload.get("sources", [])),
        }
        self._persist(record, project_id, status, signals)
        return result

    def check_project(self, project_id: str) -> dict[str, Any]:
        results = [
            self.check_runbook(record["id"], project_id)
            for record in self.runbooks.list(project_id)
        ]
        return {
            "project_id": project_id,
            "runbooks_checked": len(results),
            "stale": sum(1 for item in results if item["drift_status"] == "stale"),
            "results": results,
        }

    def _missing_or_changed_sources(
        self, project_id: str, record: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for source in payload.get("sources", []):
            item_id = source.get("item_id")
            title = source.get("title", "")
            if item_id:
                current = row(
                    "SELECT id, content, created_at FROM knowledge_items WHERE id=?", (item_id,)
                )
                if not current:
                    signals.append(
                        {
                            "type": "source_missing",
                            "severity": "stale",
                            "detail": f"Cited source '{title}' ({item_id}) is no longer in the knowledge base.",
                            "source_title": title,
                        }
                    )
                    continue
            # A newer ingestion of the same source title indicates the
            # underlying artifact changed after extraction.
            newer = rows(
                "SELECT id, content, created_at FROM knowledge_items "
                "WHERE project_id=? AND source_title=? AND created_at>? ORDER BY created_at DESC",
                (project_id, title, record["updated_at"]),
            )
            if newer:
                original_snippet = source.get("snippet", "")
                changed = original_snippet and original_snippet not in newer[0]["content"]
                if changed:
                    signals.append(
                        {
                            "type": "source_changed",
                            "severity": "possibly_stale",
                            "detail": (
                                f"Source '{title}' was re-ingested at {newer[0]['created_at']} and "
                                "no longer contains the cited passage."
                            ),
                            "source_title": title,
                            "new_content_hash": _content_hash(newer[0]["content"]),
                        }
                    )
        return signals

    def _missing_services(self, project_id: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            current = {
                str(node.get("name", "")).lower()
                for node in self.graph.list_nodes(project_id, "Service", 500)
            }
        except Exception:
            return []
        signals = []
        for service in payload.get("services", []):
            if current and service.lower() not in current:
                signals.append(
                    {
                        "type": "service_missing",
                        "severity": "stale",
                        "detail": f"Service '{service}' no longer exists in the project graph.",
                        "service": service,
                    }
                )
        return signals

    def _newer_error_evidence(
        self, project_id: str, record: dict[str, Any], payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        services = [service.lower() for service in payload.get("services", [])]
        if not services:
            return []
        newer = rows(
            "SELECT source_title, metadata_json, created_at FROM knowledge_items "
            "WHERE project_id=? AND created_at>? ORDER BY created_at DESC LIMIT 50",
            (project_id, record["updated_at"]),
        )
        hits = []
        for item in newer:
            metadata = json.loads(item["metadata_json"] or "{}")
            item_services = {str(value).lower() for value in metadata.get("services", [])}
            errors = metadata.get("signals", {}).get("errors", [])
            if errors and item_services & set(services):
                hits.append(item["source_title"])
        if not hits:
            return []
        return [
            {
                "type": "newer_error_evidence",
                "severity": "needs_human_review",
                "detail": (
                    f"{len(hits)} source(s) with error signals about {', '.join(services)} were "
                    f"ingested after this runbook was extracted: {', '.join(sorted(set(hits))[:4])}."
                ),
            }
        ]

    def _conflicting_evidence(
        self, project_id: str, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        query = " ".join(payload.get("triggers", [])[:4]) or payload.get("name", "")
        if not query:
            return []
        try:
            evidence = self.hcag.retrieve_context(project_id, query)
        except Exception:
            return []
        contradictions = detect_contradictions(evidence)
        if not contradictions:
            return []
        return [
            {
                "type": "conflicting_evidence",
                "severity": "conflicting_evidence",
                "detail": (
                    f"Current evidence contains {len(contradictions)} contradicting cause "
                    "statement pair(s) relevant to this runbook."
                ),
                "contradictions": contradictions,
            }
        ]

    @staticmethod
    def _status(signals: list[dict[str, Any]], confidence: float) -> str:
        status = "fresh"
        for signal in signals:
            severity = signal["severity"]
            if STATUS_ORDER.index(severity) > STATUS_ORDER.index(status):
                status = severity
        if status == "fresh" and confidence and confidence < 0.35:
            status = "needs_human_review"
        return status

    def _persist(
        self,
        record: dict[str, Any],
        project_id: str,
        status: str,
        signals: list[dict[str, Any]],
    ) -> None:
        payload = record["payload"]
        payload["drift_status"] = status
        payload["drift_checked_at"] = utcnow()
        with connect() as conn:
            conn.execute(
                "UPDATE runbooks SET payload_json=? WHERE id=?",
                (json.dumps(payload), record["id"]),
            )
        try:
            for signal in signals:
                signal_id = new_id("drift")
                self.graph.upsert_node(
                    "RunbookDriftSignal",
                    {
                        "id": signal_id,
                        "project_id": project_id,
                        "runbook_id": record["id"],
                        "signal_type": signal["type"],
                        "severity": signal["severity"],
                        "detail": signal["detail"],
                    },
                )
                self.graph.link(
                    "RUNBOOK_HAS_DRIFT_SIGNAL",
                    "Runbook",
                    record["id"],
                    "RunbookDriftSignal",
                    signal_id,
                )
                for assertion in rows(
                    "SELECT id, affected_runbook_ids_json FROM operational_assertions WHERE project_id=?",
                    (project_id,),
                ):
                    if record["id"] in json.loads(assertion["affected_runbook_ids_json"] or "[]"):
                        self.graph.link(
                            "DRIFT_SIGNAL_AFFECTS_ASSERTION",
                            "RunbookDriftSignal",
                            signal_id,
                            "OperationalAssertion",
                            assertion["id"],
                        )
        except Exception:
            pass  # graph unavailability must not block the drift report
        self.audit.record(
            "runbook.drift_checked",
            f"Drift check: {record['runbook_key']} is {status}",
            project_id,
            payload={"runbook_id": record["id"], "status": status, "signals": len(signals)},
        )
