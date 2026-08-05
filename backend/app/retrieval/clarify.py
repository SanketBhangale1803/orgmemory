"""Ask before acting when a request is genuinely ambiguous.

Workspace-wide memory makes vague asks dangerous rather than merely unhelpful.
"Make the background navy" is a perfectly clear sentence and a completely
ambiguous instruction when nineteen repositories are connected — and the cost of
guessing is not a bad paragraph, it is an agent editing the wrong codebase.

So this module sits between retrieval and the answer, and holds one opinion: when
the evidence itself shows the request could land in more than one place, say so
and offer the choice, rather than silently picking the top-ranked option.

There are two ways a change request fails to say enough, and both are asked about:

* **Where** — the evidence spans several projects with no clear winner.
* **What** — the request names something to change but no state to change it to.
  "Change the styling" is not a task, it is a topic. Handed to an agent it burns
  ten minutes exploring the repository before reporting back that it needed a
  target all along. Asking costs a second and is the same question, earlier.

It is deliberately conservative. Clarifying a question someone asked clearly is
its own kind of failure — the assistant that answers "which service?" to every
question is useless — so a clarification is only raised when the request is
actionable (it would change something) and one of the two gaps above is present.

Everything else is answered. Reading questions are never blocked: "what changed
recently" across five repositories is a fine question with a fine answer.
"""

from __future__ import annotations

import re
from typing import Any

from app.graph.base import GraphEvidence

# Share of the top evidence the winning project must hold to count as the obvious
# target. Below it the split is close enough that picking one is a coin flip.
# Measured as a share of hits rather than rank-weighted score: with two results,
# any decay function makes the first look dominant when it is really one-all.
DOMINANCE_SHARE = 0.6
CONSIDERED = 8
MAX_OPTIONS = 5

# Subjects broad enough that changing them is a direction, not an instruction.
# Each is a whole area of a codebase rather than a thing with a value.
TOPIC_RE = re.compile(
    r"\b(styling|styles|style|design|theme|look|appearance|ui|ux|layout|"
    r"css|formatting|branding|aesthetics|vibe|feel)\b",
    re.IGNORECASE,
)
# A destination: the state the change should end in. Any of these means the
# request said enough to act on, even if the subject was broad.
TARGET_RE = re.compile(
    # a named or literal colour
    r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|"
    r"\b(navy|blue|red|green|black|white|grey|gray|purple|orange|yellow|pink|"
    r"teal|cyan|magenta|brown|beige|maroon|gold|silver)\b|"
    # a measurement, or a named direction with a value
    r"\b\d+(\.\d+)?\s*(px|rem|em|%|pt|vh|vw|ms|s)\b|"
    # an explicit destination or comparison
    r"\bto\s+\S|\binto\s+\S|\blike\s+\S|\bmatch(es|ing)?\b|\bsame as\b|"
    r"\b(dark|light)\s*mode\b|"
    # anything quoted is a literal the asker supplied
    r"[\"'`][^\"'`]+[\"'`]",
    re.IGNORECASE,
)


def clarification(
    query: str,
    evidence: list[GraphEvidence],
    *,
    actionable: bool,
) -> dict[str, Any] | None:
    """Return a question to ask back, or None when the request is clear enough."""
    if not actionable or not evidence:
        return None

    # "What" is asked before "where": there is no point choosing a repository for
    # a task that does not yet say what it wants done.
    missing_target = _missing_target(query, evidence)
    if missing_target:
        return missing_target

    counts: dict[str, int] = {}
    labels: dict[str, str] = {}
    for item in evidence[:CONSIDERED]:
        project_id = str(item.metadata.get("project_id") or "")
        if not project_id:
            continue
        counts[project_id] = counts.get(project_id, 0) + 1
        labels.setdefault(
            project_id,
            str(item.metadata.get("project_name") or item.metadata.get("repository") or project_id),
        )

    if len(counts) < 2:
        return None

    ranked = sorted(counts.items(), key=lambda pair: pair[1], reverse=True)
    total = sum(counts.values())
    if total and ranked[0][1] / total >= DOMINANCE_SHARE:
        return None

    options = [
        {
            "project_id": project_id,
            "label": labels.get(project_id, project_id),
            "files": _files_for(evidence, project_id),
        }
        for project_id, _ in ranked[:MAX_OPTIONS]
    ]
    return {
        "reason": "ambiguous_target",
        "question": "Which codebase should I change?",
        "detail": (
            "This could apply to more than one connected repository, and I would "
            "rather ask than edit the wrong one."
        ),
        "options": options,
    }


def _missing_target(query: str, evidence: list[GraphEvidence]) -> dict[str, Any] | None:
    """Ask what the change should end up as, when the request only named a topic.

    Only fires on broad subjects. "Make the background navy" names a value and is
    left alone; "change the styling" does not, and no amount of retrieval will
    supply it, because the answer lives with the asker rather than in the code.
    """
    if not TOPIC_RE.search(query) or TARGET_RE.search(query):
        return None

    files = []
    for item in evidence[:CONSIDERED]:
        path = str(item.metadata.get("path") or "").strip()
        if path and path not in files:
            files.append(path)

    return {
        "reason": "missing_target",
        "question": "What should it change to?",
        "detail": (
            "I can see where the styling lives, but not what you want it to become. "
            "Tell me the target and I'll make the change — for example a colour, a "
            "font, or a reference to match."
        ),
        # No project_id: these are prompts to answer, not repositories to choose.
        "options": [
            {"label": "A specific colour or value", "hint": "e.g. \"make the background navy\""},
            {"label": "Match something that exists", "hint": "e.g. \"match the login page\""},
            {"label": "A direction", "hint": "e.g. \"switch it to light mode\""},
        ],
        "files": files[:4],
    }


def clarification_answer(clarify: dict[str, Any]) -> dict[str, Any]:
    """Shape a clarification as a normal grounded answer.

    It reports `sufficient: True` because withholding was the correct outcome —
    marking it insufficient would make the chat render a "not enough memory"
    apology for a question that was understood perfectly well.
    """
    listed = "\n".join(
        f"- **{option['label']}**"
        + (f" — {', '.join(option['files'][:3])}" if option.get("files") else "")
        + (f" — {option['hint']}" if option.get("hint") else "")
        for option in clarify["options"]
    )
    closing = (
        "Reply with the target and I'll make the change."
        if clarify.get("reason") == "missing_target"
        else "Tell me which one and I'll go ahead."
    )
    return {
        "answer": f"{clarify['detail']}\n\n{listed}\n\n{closing}",
        "likely_cause": "Not applicable — this is a clarifying question, not a finding.",
        "safe_actions": [],
        "approval_required": [],
        "sufficient": True,
        "answer_scope": "clarification",
        "supporting_chunk_ids": [],
        "trust_score": {
            "score": 1.0,
            "level": "clarification",
            "reason": "Asked for the missing detail instead of guessing at it.",
            "factors": {},
            "contradictions": [],
        },
    }


def _files_for(evidence: list[GraphEvidence], project_id: str) -> list[str]:
    found: list[str] = []
    for item in evidence:
        if str(item.metadata.get("project_id") or "") != project_id:
            continue
        path = str(item.metadata.get("path") or "").strip() or item.source_title
        if path and path not in found:
            found.append(path)
    return found[:4]
