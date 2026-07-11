from dataclasses import dataclass, field


@dataclass
class PolicyDecision:
    decision: str
    approval_required: bool
    approval_role: str | None
    reason: str
    risk_score: int
    factors: list[str] = field(default_factory=list)
