"""Typed response models for OrgMemory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Evidence:
    """One source-backed item used to answer a query."""

    chunk_id: str = ""
    source_type: str = ""
    source_title: str = ""
    source_url: str = ""
    source_id: str = ""
    snippet: str = ""
    exact_chunk: str = ""
    confidence: float = 0.0
    relevance: float = 0.0
    project_id: str = ""
    project_name: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Evidence:
        return cls(
            chunk_id=str(value.get("chunk_id") or ""),
            source_type=str(value.get("source_type") or ""),
            source_title=str(value.get("source_title") or ""),
            source_url=str(value.get("source_url") or ""),
            source_id=str(value.get("source_id") or ""),
            snippet=str(value.get("snippet") or ""),
            exact_chunk=str(value.get("exact_chunk") or ""),
            confidence=float(value.get("confidence") or 0.0),
            relevance=float(value.get("relevance") or 0.0),
            project_id=str(value.get("project_id") or ""),
            project_name=str(value.get("project_name") or ""),
            raw=dict(value),
        )


@dataclass(frozen=True, slots=True)
class ContextEnvelope:
    """The durable, scoped context assembled for a query."""

    id: str = ""
    project_id: str = ""
    principal_id: str = ""
    query: str = ""
    task_type: str = ""
    compiled_context: dict[str, Any] = field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()
    activation_run_ids: tuple[str, ...] = ()
    token_budget: int = 0
    expires_at: str = ""
    created_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> ContextEnvelope:
        data = value or {}
        return cls(
            id=str(data.get("id") or ""),
            project_id=str(data.get("project_id") or ""),
            principal_id=str(data.get("principal_id") or ""),
            query=str(data.get("query") or ""),
            task_type=str(data.get("task_type") or ""),
            compiled_context=dict(data.get("compiled_context") or {}),
            evidence_ids=tuple(data.get("evidence_ids") or ()),
            activation_run_ids=tuple(data.get("activation_run_ids") or ()),
            token_budget=int(data.get("token_budget") or 0),
            expires_at=str(data.get("expires_at") or ""),
            created_at=str(data.get("created_at") or ""),
            raw=dict(data),
        )


@dataclass(frozen=True, slots=True)
class AskResponse:
    """A grounded answer and all context needed to inspect or reuse it."""

    answer: str
    answer_sufficient: bool
    confidence: float
    evidence: tuple[Evidence, ...]
    context_envelope: ContextEnvelope
    trust_score: dict[str, Any] = field(default_factory=dict)
    retrieval_trace: dict[str, Any] = field(default_factory=dict)
    model: dict[str, Any] = field(default_factory=dict)
    related_services: tuple[str, ...] = ()
    memory_units: tuple[dict[str, Any], ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def compiled_context(self) -> dict[str, Any]:
        """Context ready to pass to a downstream model or agent."""

        return self.context_envelope.compiled_context

    @property
    def context_envelope_id(self) -> str:
        return self.context_envelope.id

    @property
    def swarm_run_ids(self) -> tuple[str, ...]:
        return self.context_envelope.activation_run_ids

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> AskResponse:
        return cls(
            answer=str(value.get("answer") or ""),
            answer_sufficient=bool(value.get("answer_sufficient")),
            confidence=float(value.get("confidence") or 0.0),
            evidence=tuple(
                Evidence.from_dict(item)
                for item in value.get("evidence") or ()
                if isinstance(item, dict)
            ),
            context_envelope=ContextEnvelope.from_dict(value.get("context_envelope")),
            trust_score=dict(value.get("trust_score") or {}),
            retrieval_trace=dict(value.get("retrieval_trace") or {}),
            model=dict(value.get("model") or {}),
            related_services=tuple(value.get("related_services") or ()),
            memory_units=tuple(value.get("memory_units") or ()),
            raw=dict(value),
        )
