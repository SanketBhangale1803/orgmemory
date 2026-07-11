"""Evidence-limited change impact analysis over persisted graph relationships."""

from __future__ import annotations

import json
from typing import Any

from app.audit import AuditService
from app.core.database import connect, new_id, row, rows, utcnow
from app.graph.base import GraphStore
from app.reliability.assertions import OperationalAssertionService


class ChangeImpactService:
    def __init__(
        self,
        graph: GraphStore,
        assertions: OperationalAssertionService,
        audit: AuditService | None = None,
    ):
        self.graph = graph
        self.assertions = assertions
        self.audit = audit or AuditService()

    def analyze(self, project_id: str, change: dict[str, Any]) -> dict[str, Any]:
        change = self._materialize_change(project_id, dict(change or {}))
        changed = self._changed_scope(project_id, change)
        impact_id = new_id("impact")
        assertions = self.assertions.list(project_id)
        runbooks = {
            item["id"]: item
            for item in rows(
                "SELECT id,runbook_key,name,risk_level,payload_json FROM runbooks WHERE project_id=?",
                (project_id,),
            )
        }
        impacts = []
        for assertion in assertions:
            connection = self._connection(assertion, changed, runbooks)
            if not connection:
                continue
            if assertion["status"] == "verified":
                assertion = self.assertions.flag_possibly_stale(assertion["id"], connection["why"])
            status = (
                assertion["status"]
                if assertion["status"] in {"stale", "contradicted"}
                else "possibly_stale"
            )
            severity = self._severity(assertion, connection, runbooks)
            impacts.append(
                {
                    "assertion_id": assertion["id"],
                    "assertion_title": assertion["title"],
                    "status": status,
                    "severity": severity,
                    "why_affected": connection["why"],
                    "connection": connection["kind"],
                    "affected_service": connection.get("service", "unknown"),
                    "environment_scope": assertion["environment_scope"],
                    "verification_owner": assertion["verification_owner"] or "owner unknown",
                    "recommended_action": self._action(assertion, status),
                    "evidence": connection["evidence"],
                    "inference": connection["kind"] != "direct_graph_edge",
                    "affected_runbook_ids": assertion["affected_runbook_ids"],
                    "affected_runbook_step_ids": assertion["affected_runbook_step_ids"],
                }
            )
        impacts.sort(
            key=lambda item: (
                {"critical": 4, "high": 3, "medium": 2, "low": 1}[item["severity"]],
                item["assertion_title"],
            ),
            reverse=True,
        )
        summary = self._summary(changed, impacts)
        report = {
            "id": impact_id,
            "project_id": project_id,
            "change_type": change.get("type", "repository_reingestion"),
            "change_ref": str(change.get("ref") or change.get("id") or "current-source"),
            "severity": impacts[0]["severity"] if impacts else "low",
            "status": "action_required" if impacts else "no_connected_impact",
            "summary": summary,
            "created_at": utcnow(),
            "observability": {
                "status": "not_connected",
                "basis": "code/config evidence only; no runtime telemetry was queried.",
            },
            "changed": changed,
            "impacts": impacts,
            "evidence_limit": "A connected source changed. This is evidence to verify the procedure, not proof that the runbook is invalid.",
        }
        with connect() as conn:
            conn.execute(
                "INSERT INTO change_impacts VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    impact_id,
                    project_id,
                    report["change_type"],
                    report["change_ref"],
                    report["status"],
                    report["severity"],
                    summary,
                    json.dumps(report),
                    report["created_at"],
                    report["created_at"],
                ),
            )
        self.graph.upsert_change_impact(
            {
                "id": impact_id,
                "project_id": project_id,
                "change_type": report["change_type"],
                "change_ref": report["change_ref"],
                "severity": report["severity"],
                "status": report["status"],
            }
        )
        self._link_graph(report)
        self.audit.record(
            "change_impact.analyzed",
            summary,
            project_id,
            payload={
                "impact_id": impact_id,
                "affected_assertions": len(impacts),
                "basis": "code_config_only",
            },
        )
        return report

    def list(self, project_id: str) -> list[dict[str, Any]]:
        return [
            json.loads(item["payload_json"])
            for item in rows(
                "SELECT payload_json FROM change_impacts WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            )
        ]

    def get(self, impact_id: str, project_id: str | None = None) -> dict[str, Any] | None:
        sql, params = "SELECT payload_json FROM change_impacts WHERE id=?", (impact_id,)
        if project_id:
            sql += " AND project_id=?"
            params += (project_id,)
        record = row(sql, params)
        return json.loads(record["payload_json"]) if record else None

    def _changed_scope(self, project_id: str, change: dict[str, Any]) -> dict[str, Any]:
        files = sorted(set(change.get("changed_files") or change.get("files") or []))
        file_ids = {f"file:{project_id}:{path}" for path in files}
        edges = self.graph.list_edges(project_id, limit=5000)
        nodes = {node.get("id"): node for node in self.graph.list_nodes(project_id, limit=5000)}
        related_ids = set(file_ids)
        for edge in edges:
            if edge.get("from_id") in file_ids or edge.get("to_id") in file_ids:
                related_ids.update({edge.get("from_id", ""), edge.get("to_id", "")})
        services = sorted(
            {
                str(nodes[node_id].get("name", ""))
                for node_id in related_ids
                if nodes.get(node_id, {}).get("node_type") == "Service"
                and nodes[node_id].get("name")
            }
            | set(change.get("services") or [])
        )
        env_vars = sorted(
            {
                str(nodes[node_id].get("name", ""))
                for node_id in related_ids
                if nodes.get(node_id, {}).get("node_type") == "EnvironmentVariable"
                and nodes[node_id].get("name")
            }
            | set(change.get("environment_variables") or [])
        )
        config_keys = sorted(
            {
                str(nodes[node_id].get("name", ""))
                for node_id in related_ids
                if nodes.get(node_id, {}).get("node_type") == "ConfigKey"
                and nodes[node_id].get("name")
            }
            | set(change.get("config_keys") or [])
        )
        commands = sorted(
            {
                str(nodes[node_id].get("command", ""))
                for node_id in related_ids
                if nodes.get(node_id, {}).get("node_type") == "Command"
                and nodes[node_id].get("command")
            }
            | set(change.get("commands") or [])
        )
        return {
            "files": files,
            "file_ids": sorted(file_ids),
            "related_ids": sorted(related_ids),
            "services": services,
            "environment_variables": env_vars,
            "config_keys": config_keys,
            "commands": commands,
            "workflows": list(change.get("workflows") or []),
            "dependencies": list(change.get("dependencies") or []),
            "source_evidence": list(change.get("evidence") or []),
        }

    @staticmethod
    def _materialize_change(project_id: str, change: dict[str, Any]) -> dict[str, Any]:
        """Resolve retained PR/commit ingestion metadata when a caller supplies its ref."""
        if change.get("changed_files") or change.get("type") not in {
            "github_pull_request",
            "commit",
        }:
            return change
        ref = str(change.get("ref", ""))
        if not ref:
            return change
        item = row(
            """SELECT source_id,source_title,source_url,content,metadata_json FROM knowledge_items
            WHERE project_id=? AND source_type='pull_request'
            AND (source_id=? OR source_url=? OR source_title LIKE ?)
            ORDER BY created_at DESC LIMIT 1""",
            (project_id, ref, ref, f"%{ref}%"),
        )
        if not item:
            return change
        metadata = json.loads(item["metadata_json"] or "{}")
        change["changed_files"] = metadata.get("changed_files", [])
        change["evidence"] = [
            {
                "kind": "ingested_github_pull_request",
                "source_item_id": item["source_id"],
                "source_url": item["source_url"],
                "commit_sha": metadata.get("commit_sha", ""),
                "detail": f"{item['source_title']} changed {len(change['changed_files'])} retained file(s).",
                "snippet": item["content"][:500],
            }
        ]
        return change

    def _connection(
        self, assertion: dict[str, Any], changed: dict[str, Any], runbooks: dict[str, Any]
    ) -> dict[str, Any] | None:
        subject_id = assertion["subject_id"]
        direct = subject_id in changed["related_ids"] or subject_id in changed["file_ids"]
        evidence = list(changed["source_evidence"])
        if direct:
            return {
                "kind": "direct_graph_edge",
                "why": f"The changed source is directly connected to assertion subject {subject_id} in the graph.",
                "evidence": evidence,
                "service": self._service_for(subject_id, changed),
            }
        # The assertion can still be connected through a runbook whose services overlap a changed service.
        for runbook_id in assertion["affected_runbook_ids"]:
            runbook = runbooks.get(runbook_id)
            if not runbook:
                continue
            payload = json.loads(runbook["payload_json"])
            overlap = sorted(set(payload.get("services", [])) & set(changed["services"]))
            if overlap:
                return {
                    "kind": "runbook_service_overlap",
                    "why": f"The assertion's runbook applies to changed service(s): {', '.join(overlap)}.",
                    "evidence": evidence,
                    "service": overlap[0],
                }
        return None

    @staticmethod
    def _service_for(subject_id: str, changed: dict[str, Any]) -> str:
        return changed["services"][0] if changed["services"] else "unknown"

    @staticmethod
    def _severity(
        assertion: dict[str, Any], connection: dict[str, Any], runbooks: dict[str, Any]
    ) -> str:
        if assertion["status"] == "contradicted" and assertion["environment_scope"] == "production":
            return "critical"
        production = assertion["environment_scope"] == "production"
        if production and connection["kind"] == "direct_graph_edge":
            return "high"
        if connection["kind"] == "direct_graph_edge":
            return "medium"
        return "low"

    @staticmethod
    def _action(assertion: dict[str, Any], status: str) -> str:
        if status == "contradicted":
            return "update runbook"
        if status == "stale":
            return "update runbook"
        if assertion.get("policy_status") == "dismissed":
            return "dismiss with reason"
        if assertion.get("approval_requirement") == "admin_review_required":
            return "approve exception"
        return "verify"

    @staticmethod
    def _summary(changed: dict[str, Any], impacts: list[dict[str, Any]]) -> str:
        if not changed["files"] and not changed["source_evidence"]:
            return "No connected change data was supplied; no impact conclusion was made."
        if not impacts:
            return (
                "Change evidence was recorded, but no connected operational assertions were found."
            )
        return f"{len(impacts)} operational assertion(s) need review after code/config evidence changed."

    def _link_graph(self, report: dict[str, Any]) -> None:
        for file_id in report["changed"]["file_ids"]:
            self.graph.link(
                "CHANGE_IMPACT_TOUCHES_SOURCE", "ChangeImpact", report["id"], "File", file_id
            )
        for impact in report["impacts"]:
            self.graph.link(
                "CHANGE_IMPACT_FOR_ASSERTION",
                "ChangeImpact",
                report["id"],
                "OperationalAssertion",
                impact["assertion_id"],
            )
            for runbook_id in impact["affected_runbook_ids"]:
                self.graph.link(
                    "CHANGE_IMPACT_AFFECTS_RUNBOOK",
                    "ChangeImpact",
                    report["id"],
                    "Runbook",
                    runbook_id,
                )
            for step_id in impact["affected_runbook_step_ids"]:
                self.graph.link(
                    "CHANGE_IMPACT_AFFECTS_RUNBOOK_STEP",
                    "ChangeImpact",
                    report["id"],
                    "RunbookStep",
                    step_id,
                )
