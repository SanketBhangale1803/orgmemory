from __future__ import annotations

import importlib.util
import sys

from app.core.config import settings

from .models import PolicyDecision
from .policy import product_policy


class AgentGateAdapter:
    def __init__(self):
        self.engine = None
        self.mode = "runbook_policy"
        try:
            package_name = "_runbook_agentgate"
            package_dir = settings.agentgate_path / "app"
            spec = importlib.util.spec_from_file_location(
                package_name,
                package_dir / "__init__.py",
                submodule_search_locations=[str(package_dir)],
            )
            if not spec or not spec.loader:
                raise ImportError
            package = importlib.util.module_from_spec(spec)
            sys.modules[package_name] = package
            spec.loader.exec_module(package)
            module_spec = importlib.util.spec_from_file_location(
                f"{package_name}.policy_engine", package_dir / "policy_engine.py"
            )
            if not module_spec or not module_spec.loader:
                raise ImportError
            module = importlib.util.module_from_spec(module_spec)
            sys.modules[module_spec.name] = module
            module_spec.loader.exec_module(module)
            self.engine = module.PolicyEngine(settings.agentgate_path / "policies" / "default.yaml")
            self.mode = "agentgate+runbook_policy"
        except Exception:
            self.engine = None

    def evaluate(self, action_type: str, params: dict, action_id: str) -> PolicyDecision:
        local = product_policy(
            action_type,
            str(params.get("environment", "")),
            bool(params.get("admin_approval_requested")),
        )
        if not self.engine:
            return local
        external = self.engine.evaluate(
            agent_id="engineering-agent",
            tool_name=f"runbook.{action_id}",
            action_type=action_type,
            args=params,
            reason=f"Proposed runbook step {action_id}",
            user_id="demo-user",
        )
        if external.decision == "deny":
            return PolicyDecision(
                "deny",
                False,
                None,
                external.reason,
                external.risk_score,
                list(external.risk_factors),
            )
        local.risk_score = max(local.risk_score, external.risk_score)
        local.factors.extend(external.risk_factors)
        return local
