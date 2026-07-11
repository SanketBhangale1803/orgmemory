from __future__ import annotations

import json
import re
from typing import Any

from app.core.config import settings
from app.graph.base import GraphEvidence

CAUSE_MARKERS = (
    "root cause",
    "caused by",
    "because",
    "due to",
    "mismatch",
    "failed",
    "failure",
    "timeout",
    "refused",
    "unreachable",
    "error",
)
ACTION_MARKERS = (
    "check",
    "inspect",
    "verify",
    "review",
    "compare",
    "restart",
    "update",
    "change",
    "deploy",
    "rotate",
    "send",
    "delete",
)
MUTATION_MARKERS = (
    "restart",
    "update",
    "change",
    "deploy",
    "rotate",
    "delete",
    "write",
    "remove",
    "scale",
)
OVERVIEW_PHRASES = (
    "what is this",
    "what does this",
    "what is the project",
    "what is the service",
    "what does it do",
    "tell me about",
    "project overview",
    "service overview",
    "describe this",
)


def sentences(text: str) -> list[str]:
    lines = [line.strip(" -*#\t") for line in text.splitlines() if line.strip()]
    output: list[str] = []
    for line in lines:
        output.extend(
            piece.strip() for piece in re.split(r"(?<=[.!?])\s+", line) if len(piece.strip()) >= 12
        )
    return output


def evidence_answer(query: str, evidence: list[GraphEvidence]) -> dict[str, Any]:
    if not evidence:
        return _insufficient()
    if _overview_intent(query):
        return _overview_answer(evidence)
    query_terms = {value.lower() for value in re.findall(r"[A-Za-z][\w-]{2,}", query)} - {
        "runbook",
        "why",
        "how",
        "what",
        "this",
        "that",
        "service",
    }
    candidates: list[tuple[float, str, GraphEvidence]] = []
    for item in evidence:
        for sentence in sentences(item.text):
            lowered = sentence.lower()
            overlap = sum(term in lowered for term in query_terms)
            causal = sum(marker in lowered for marker in CAUSE_MARKERS)
            explicit_cause = (
                6
                if "root cause" in lowered
                else (
                    4
                    if "caused by" in lowered
                    else 2 if "because" in lowered or "due to" in lowered else 0
                )
            )
            score = overlap * 2.0 + causal * 1.5 + explicit_cause + item.score / 20
            if score > 0:
                candidates.append((score, sentence, item))
    candidates.sort(key=lambda value: value[0], reverse=True)
    if not candidates or candidates[0][0] < 2.0:
        return _insufficient()
    likely_cause = candidates[0][1]
    supporting: list[str] = []
    for _, sentence, _ in candidates:
        if sentence != likely_cause and sentence not in supporting:
            supporting.append(sentence)
        if len(supporting) == 2:
            break
    actions = _actions(evidence)
    answer = f"The strongest retrieved evidence indicates: {likely_cause}"
    if supporting:
        answer += " Supporting evidence also notes: " + " ".join(supporting)
    return {
        "answer": answer,
        "likely_cause": likely_cause,
        "safe_actions": actions[0],
        "approval_required": actions[1],
        "sufficient": True,
    }


def _overview_intent(query: str) -> bool:
    lowered = " ".join(query.lower().replace("@runbook", "").split())
    return any(phrase in lowered for phrase in OVERVIEW_PHRASES)


def _overview_answer(evidence: list[GraphEvidence]) -> dict[str, Any]:
    candidates: list[tuple[float, str]] = []
    for item in evidence:
        source_weight = 5 if item.source_title.lower().startswith("readme") else 2
        for sentence in sentences(item.text):
            lowered = sentence.lower()
            if (
                sentence.startswith(("![", "[", "```"))
                or "`" in sentence
                or "http://" in lowered
                or "https://" in lowered
            ):
                continue
            descriptive = sum(
                marker in lowered
                for marker in (
                    " is a ",
                    " is an ",
                    "designed for",
                    "features",
                    "provides",
                    "system",
                    "application",
                )
            )
            score = source_weight + descriptive * 2 + min(len(sentence), 240) / 240
            if descriptive and 24 <= len(sentence) <= 420:
                candidates.append((score, sentence))
    candidates.sort(key=lambda value: value[0], reverse=True)
    selected: list[str] = []
    for _, sentence in candidates:
        if sentence not in selected:
            selected.append(sentence)
        if len(selected) == 2:
            break
    if not selected:
        return _insufficient()
    return {
        "answer": "Based on the retrieved project sources: " + " ".join(selected),
        "likely_cause": "Not applicable — this is a project overview question.",
        "safe_actions": [],
        "approval_required": [],
        "sufficient": True,
    }


def _actions(evidence: list[GraphEvidence]) -> tuple[list[str], list[str]]:
    safe: list[str] = []
    risky: list[str] = []
    for item in evidence:
        signals = item.metadata.get("signals", {})
        candidates = list(signals.get("procedures", [])) + list(signals.get("commands", []))
        for candidate in candidates:
            lowered = candidate.lower()
            if not any(marker in lowered for marker in ACTION_MARKERS):
                continue
            target = risky if any(marker in lowered for marker in MUTATION_MARKERS) else safe
            if candidate not in target:
                target.append(candidate)
    return safe[:5], risky[:5]


def _insufficient() -> dict[str, Any]:
    return {
        "answer": "I do not have enough evidence to answer this confidently.",
        "likely_cause": "Insufficient evidence",
        "safe_actions": [],
        "approval_required": [],
        "sufficient": False,
    }


def llm_answer(query: str, evidence: list[GraphEvidence]) -> dict[str, Any] | None:
    if not settings.openai_api_key or not evidence:
        return None
    try:
        from openai import OpenAI

        source_text = "\n\n".join(
            f"[{index}] {item.source_title}\n{item.text}" for index, item in enumerate(evidence, 1)
        )
        prompt = (
            "Answer using only the supplied evidence. Do not add operational facts. "
            "Return JSON with answer, likely_cause, safe_actions, approval_required. "
            "If evidence is inadequate, use exactly 'I do not have enough evidence to answer this confidently.'\n"
            f"Question: {query}\nEvidence:\n{source_text}"
        )
        response = OpenAI(api_key=settings.openai_api_key).chat.completions.create(
            model=settings.openai_model,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        result = json.loads(response.choices[0].message.content or "{}")
        if result.get("answer"):
            result["sufficient"] = not result["answer"].startswith("I do not have enough evidence")
            return result
    except Exception:
        return None
    return None
