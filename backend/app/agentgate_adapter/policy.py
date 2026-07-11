from __future__ import annotations

from .models import PolicyDecision

ALLOWED = {"read_only", "analysis", "draft_change"}
APPROVAL = {"mutation", "external_send", "deployment", "production_change", "data_export"}


def product_policy(
    action_type: str, environment: str = "", admin_requested: bool = False
) -> PolicyDecision:
    action_type = action_type.lower()
    production = environment.lower() in {"prod", "production"}
    if action_type == "credential_access":
        return PolicyDecision(
            decision="require_approval" if admin_requested else "deny",
            approval_required=admin_requested,
            approval_role="admin" if admin_requested else None,
            reason="Credential access is denied unless explicit admin approval is requested.",
            risk_score=95,
            factors=["credential access", "admin boundary"],
        )
    if action_type in APPROVAL or production:
        role = "admin" if production or action_type == "production_change" else "human"
        reason = (
            f"{action_type.replace('_', ' ').title()} in production requires admin approval "
            "because it changes or exports state."
            if production
            else f"{action_type.replace('_', ' ').title()} changes or exports state and requires human approval."
        )
        return PolicyDecision(
            decision="require_approval",
            approval_required=True,
            approval_role=role,
            reason=reason,
            risk_score=85 if production else 65,
            factors=[action_type, environment or "unspecified environment"],
        )
    if action_type in ALLOWED:
        return PolicyDecision(
            "allow",
            False,
            None,
            "Read, analysis, and draft actions are allowed.",
            15,
            [action_type],
        )
    return PolicyDecision(
        "require_approval",
        True,
        "human",
        "Unknown action type fails closed.",
        70,
        ["unknown action type"],
    )
