from __future__ import annotations

import json
from typing import Any

from app.agentgate_adapter import AgentGateAdapter
from app.audit import AuditService
from app.core.config import settings
from app.core.database import connect, new_id, row, rows, utcnow
from app.graph.base import GraphStore
from app.reliability import OperationalAssertionService
from app.runbooks import RunbookService


class ApprovalService:
    def __init__(
        self,
        graph: GraphStore,
        runbooks: RunbookService,
        gate: AgentGateAdapter | None = None,
        audit: AuditService | None = None,
    ):
        self.graph = graph
        self.runbooks = runbooks
        self.gate = gate or AgentGateAdapter()
        self.audit = audit or AuditService()
        self.assertions = OperationalAssertionService(graph, self.audit)

    def propose(
        self, project_id: str, runbook_id: str, action_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        runbook = self.runbooks.get(runbook_id, project_id)
        if not runbook:
            raise ValueError("Runbook not found")
        payload = runbook["payload"]
        step = next((item for item in payload["steps"] if item["id"] == action_id), None)
        if not step:
            raise ValueError("Runbook step not found")
        command = self._render(step.get("command_template", ""), params)
        decision = self.gate.evaluate(step["action_type"], params, action_id)
        linked_assertions = self.assertions.applicable_to_step(project_id, runbook["id"], action_id)
        unresolved = [
            item
            for item in linked_assertions
            if item["status"] in {"proposed", "possibly_stale", "stale", "contradicted"}
            and item.get("policy_status") != "dismissed"
        ]
        production_changing = str(params.get("environment", "")).lower() in {
            "prod",
            "production",
        } and step["action_type"] not in {"read_only", "analysis"}
        assertion_policy = None
        if production_changing and unresolved and decision.decision != "deny":
            # An unresolved production claim is never a trusted basis for a proposal.
            decision.decision = "require_approval"
            decision.approval_required = True
            decision.approval_role = "admin"
            decision.risk_score = max(decision.risk_score, 90)
            decision.reason += " Reliability gate: linked operational assertions are unresolved; admin verification or approval is required."
            decision.factors.append("unresolved operational assertion")
            assertion_policy = {
                "trusted": False,
                "reason": "Unresolved assertion blocks trust for this production-changing proposal.",
                "assertion_ids": [item["id"] for item in unresolved],
            }
        action_record_id = new_id("action")
        status = (
            "pending"
            if decision.approval_required
            else "denied" if decision.decision == "deny" else "allowed"
        )
        now = utcnow()
        summary = step["description"]
        with connect() as conn:
            conn.execute(
                "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    action_record_id,
                    project_id,
                    runbook["id"],
                    action_id,
                    step["action_type"],
                    summary,
                    command,
                    json.dumps(params),
                    decision.decision,
                    status,
                    decision.reason,
                    decision.risk_score,
                    now,
                    None,
                    None,
                ),
            )
        graph_action = {
            "id": action_record_id,
            "project_id": project_id,
            "runbook_id": runbook["id"],
            "action_type": step["action_type"],
            "status": status,
            "reason": decision.reason,
        }
        self.graph.upsert_agent_action(graph_action)
        if decision.approval_required:
            self.graph.link(
                "ACTION_REQUIRES_APPROVAL",
                "AgentAction",
                action_record_id,
                "RunbookStep",
                f"{runbook['id']}:{action_id}",
            )
        self.audit.record(
            "action.proposed",
            summary,
            project_id,
            payload={
                "action_id": action_record_id,
                "decision": decision.decision,
                "command_preview": command,
                "policy_engine": self.gate.mode,
                "assertion_policy": assertion_policy,
            },
        )
        return {
            "action_id": action_record_id,
            "allowed": status == "allowed",
            "approval_required": decision.approval_required,
            "status": status,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "approval_role": decision.approval_role,
            "command_preview": command,
            "execution_mode": (
                "would_execute"
                if settings.runbook_demo_mode or not settings.allow_local_command_execution
                else "enabled"
            ),
            "assertion_policy": assertion_policy or {"trusted": True, "assertion_ids": []},
        }

    def resolve(self, action_id: str, approved: bool, resolved_by: str) -> dict[str, Any]:
        action = row("SELECT * FROM actions WHERE id=?", (action_id,))
        if not action:
            raise ValueError("Action not found")
        if action["status"] != "pending":
            raise ValueError("Action is not pending")
        status = "approved" if approved else "denied"
        now = utcnow()
        with connect() as conn:
            conn.execute(
                "UPDATE actions SET status=?,resolved_at=?,resolved_by=? WHERE id=?",
                (status, now, resolved_by, action_id),
            )
        self.graph.upsert_agent_action(
            {
                "id": action_id,
                "project_id": action["project_id"],
                "status": status,
                "resolved_at": now,
                "resolved_by": resolved_by,
            }
        )
        self.audit.record(
            f"action.{status}",
            f"Action {status} by {resolved_by}",
            action["project_id"],
            resolved_by,
            {"action_id": action_id, "command_preview": action["command_preview"]},
        )
        return {
            "action_id": action_id,
            "status": status,
            "resolved_by": resolved_by,
            "command_preview": action["command_preview"],
            "execution_mode": (
                "would_execute"
                if settings.runbook_demo_mode or not settings.allow_local_command_execution
                else "enabled"
            ),
        }

    def list(
        self, status: str | None = None, project_id: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if status:
            clauses.append("status=?")
            params.append(status)
        if project_id:
            clauses.append("project_id=?")
            params.append(project_id)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        records = rows(f"SELECT * FROM actions{where} ORDER BY requested_at DESC", tuple(params))
        for record in records:
            record["params"] = json.loads(record.pop("params_json"))
        return records

    @staticmethod
    def _render(template: str, params: dict[str, Any]) -> str:
        command = template
        for key, value in params.items():
            command = command.replace("{" + key + "}", str(value))
        return command
