from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.graph.base import GraphEvidence


@dataclass
class AgentReport:
    """Typed output from one independently executing activation specialist."""

    agent: str
    role: str
    project_id: str
    status: str
    candidates: list[GraphEvidence] = field(default_factory=list)
    latency_ms: int = 0
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def public_summary(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "role": self.role,
            "project_id": self.project_id,
            "status": self.status,
            "candidate_count": len(self.candidates),
            "candidate_ids": [item.chunk_id for item in self.candidates],
            "latency_ms": self.latency_ms,
            "details": self.details,
            "error": self.error,
        }


@dataclass
class CompiledActivation:
    """The compiler's bounded evidence set and durable context artifact."""

    run_id: str
    evidence: list[GraphEvidence]
    compiled_context: dict[str, Any]
    trace: dict[str, Any]
