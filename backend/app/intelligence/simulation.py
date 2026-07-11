"""Runbook simulation (dry run).

A simulation walks a real runbook's steps through the same AgentGate policy
evaluation used by live proposals, without creating actions or executing
anything. It reports, per step: the policy decision, whether approval would
be required, unresolved command parameters (missing context), and whether
the step is dangerous. It also reports which evidence backs the runbook and
what would still be needed before an agent could execute it.

If no runbook applies to the scenario, the simulation says so honestly.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from app.agentgate_adapter import AgentGateAdapter
from app.audit import AuditService
from app.core.database import rows

if TYPE_CHECKING:
    from app.runbooks import RunbookService

PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][\w]*)\}")
DANGEROUS_TYPES = {
    "mutation",
    "deployment",
    "production_change",
    "database_write",
    "infra_change",
    "credential_access",
    "customer_impacting_action",
    "external_send",
    "data_export",
}


class SimulationService:
    def __init__(
        self,
        runbooks: RunbookService,
        gate: AgentGateAdapter | None = None,
        audit: AuditService | None = None,
    ):
        self.runbooks = runbooks
        self.gate = gate or AgentGateAdapter()
        self.audit = audit or AuditService()

    def simulate(
        self,
        project_id: str,
        runbook_id: str | None = None,
        scenario: str = "",
        environment: str = "production",
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = dict(params or {})
        params.setdefault("environment", environment)
        record, selection_reason = self._select_runbook(project_id, runbook_id, scenario)
        if not record:
            result = {
                "project_id": project_id,
                "scenario": scenario,
                "applicable_runbook": None,
                "steps": [],
                "verdict": "no_applicable_runbook",
                "reason": selection_reason,
            }
            self.audit.record(
                "simulation.run", scenario or "simulation", project_id, payload=result
            )
            return result

        payload = record["payload"]
        steps: list[dict[str, Any]] = []
        approvals_required: list[str] = []
        missing_context: set[str] = set()
        dangerous: list[str] = []
        for step in payload.get("steps", []):
            decision = self.gate.evaluate(step["action_type"], params, step["id"])
            template = step.get("command_template", "")
            unresolved = sorted(
                name for name in PLACEHOLDER_RE.findall(template) if name not in params
            )
            missing_context.update(unresolved)
            is_dangerous = step["action_type"] in DANGEROUS_TYPES
            if is_dangerous:
                dangerous.append(step["id"])
            if decision.approval_required:
                approvals_required.append(step["id"])
            steps.append(
                {
                    "step_id": step["id"],
                    "description": step["description"],
                    "action_type": step["action_type"],
                    "policy_decision": decision.decision,
                    "approval_required": decision.approval_required,
                    "approval_role": decision.approval_role,
                    "risk_score": decision.risk_score,
                    "policy_reason": decision.reason,
                    "command_preview": template,
                    "unresolved_params": unresolved,
                    "dangerous": is_dangerous,
                    "would_execute": False,
                }
            )

        evidence_needed = [
            f"Provide value for parameter '{name}'" for name in sorted(missing_context)
        ]
        for context in payload.get("required_context", []):
            evidence_needed.append(f"Confirm: {context}")

        verdict = (
            "blocked_without_approvals"
            if approvals_required
            else "executable_read_only" if steps else "no_steps"
        )
        result = {
            "project_id": project_id,
            "scenario": scenario,
            "environment": environment,
            "applicable_runbook": {
                "id": record["id"],
                "runbook_key": record["runbook_key"],
                "name": payload.get("name"),
                "confidence": payload.get("confidence"),
                "risk_level": payload.get("risk_level"),
                "drift_status": payload.get("drift_status", "unchecked"),
                "version": payload.get("version", 1),
            },
            "selection_reason": selection_reason,
            "steps": steps,
            "approvals_required": approvals_required,
            "dangerous_steps": dangerous,
            "missing_context": sorted(missing_context),
            "evidence_needed_before_execution": evidence_needed,
            "sources": payload.get("sources", []),
            "policy_engine": self.gate.mode,
            "verdict": verdict,
        }
        self.audit.record(
            "simulation.run",
            f"Simulated {payload.get('name', record['runbook_key'])} in {environment}",
            project_id,
            payload={
                "runbook_id": record["id"],
                "verdict": verdict,
                "approvals_required": approvals_required,
                "dangerous_steps": dangerous,
            },
        )
        return result

    def _select_runbook(
        self, project_id: str, runbook_id: str | None, scenario: str
    ) -> tuple[dict[str, Any] | None, str]:
        if runbook_id:
            record = self.runbooks.get(runbook_id, project_id)
            if record:
                return record, "Runbook selected explicitly."
            return None, f"Runbook '{runbook_id}' was not found in this project."
        if not scenario:
            return None, "No runbook id or scenario provided."
        terms = {
            term.lower()
            for term in re.findall(r"[A-Za-z][\w-]{3,}", scenario)
            if term.lower() not in {"simulate", "simulation", "outage", "incident", "failure"}
        }
        best: tuple[int, dict[str, Any] | None] = (0, None)
        for record in rows(
            "SELECT id, runbook_key, payload_json FROM runbooks WHERE project_id=?", (project_id,)
        ):
            payload = json.loads(record["payload_json"])
            haystack = " ".join(
                [
                    record["runbook_key"],
                    payload.get("name", ""),
                    " ".join(payload.get("services", [])),
                    " ".join(str(value) for value in payload.get("triggers", [])),
                ]
            ).lower()
            score = sum(1 for term in terms if term in haystack)
            if score > best[0]:
                best = (score, record)
        if not best[1]:
            return None, (
                "No extracted runbook matches this scenario. Extract a runbook from evidence "
                "first, then simulate it."
            )
        return self.runbooks.get(best[1]["id"], project_id), (
            f"Selected '{best[1]['runbook_key']}' — it matches {best[0]} scenario term(s)."
        )
