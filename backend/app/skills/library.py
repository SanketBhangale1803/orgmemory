"""Skills distilled from work that verifiably worked.

`skill_specs` (in :mod:`app.memory.brain`) compiles what a company has *written
down* — documented procedures and policies. This module records the other half:
what actually **worked** when someone did the thing. A successful execution run
already contains the whole lesson — the request, the files it touched, the
approach, and a commit proving it landed — and throwing that away means the next
person re-derives it from scratch.

The discipline is "never do one-off work": if a question has to be worked out
twice, the first answer was wasted.

The obvious way to build this is also the wrong way. Recording every success as a
reusable skill produces a confident library of superstitions, and a bad skill
encodes a bad process forever. So three rules keep the library worth reading
from rather than merely large:

* **One success is a coincidence.** A new skill is `proposed`, not `active`, and
  is never injected into a prompt until it has worked again. Skills earn trust.
* **Similar work reinforces rather than duplicates.** A near-identical success
  strengthens the existing skill instead of adding a second copy of it, so the
  library stays small enough to actually be selective.
* **Skills that stop working are retired.** When a reused skill precedes a
  failure it loses confidence, and a skill that fails more than it succeeds is
  retired automatically with the reason recorded.

Matching is deterministic token and file overlap: it must be explainable, must
cost nothing, and must not hallucinate a precedent that never happened.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.database import connect, decode, new_id, rows, utcnow

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_.-]{1,}")
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "get", "give", "has", "have", "how", "i", "in", "is", "it", "its", "me", "my", "of",
    "on", "or", "our", "please", "should", "show", "than", "that", "the", "then", "there",
    "this", "to", "us", "was", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "you", "your",
})

# A skill must work at least this many times before it is trusted enough to be
# put in front of an agent. Two is the smallest number that distinguishes a
# repeatable approach from a one-off that happened to land.
TRUST_THRESHOLD = 2
# Above this trigger overlap, two requests are the same job and should reinforce
# one skill rather than create a second.
SAME_JOB_SIMILARITY = 0.6
# Below this, a candidate is not similar enough to be worth an agent's attention.
MATCH_FLOOR = 0.3
MAX_INJECTED = 3


def distil(
    *,
    project_id: str,
    task: str,
    files: list[str],
    approach: str = "",
    workspace_id: str = "",
    run_id: str = "",
    context_event_id: str = "",
    commit_sha: str = "",
) -> dict[str, Any] | None:
    """Record that this approach worked, as a new skill or a reinforcement.

    Returns the skill, or None when there is nothing worth remembering.
    """
    tokens = _tokens(task)
    if not tokens or not files:
        # Without a trigger or a place, there is nothing a future task could match.
        return None

    existing = _closest(project_id, tokens, threshold=SAME_JOB_SIMILARITY)
    if existing:
        return _reinforce(existing, files, run_id, context_event_id, commit_sha)

    now = utcnow()
    skill_id = new_id("skl")
    with connect() as conn:
        conn.execute(
            "INSERT INTO learned_skills ("
            "id, workspace_id, project_id, name, trigger, trigger_tokens_json, approach,"
            "files_json, status, uses, successes, failures, confidence, run_ids_json,"
            "context_ids_json, commits_json, created_at, updated_at, last_used_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                skill_id,
                workspace_id,
                project_id,
                _name(task),
                task.strip()[:500],
                json.dumps(sorted(tokens)),
                approach.strip()[:2000],
                json.dumps(files[:12]),
                # Proposed, not active: it has worked exactly once so far.
                "proposed",
                1,
                1,
                0,
                _confidence(1, 0),
                json.dumps([run_id] if run_id else []),
                json.dumps([context_event_id] if context_event_id else []),
                json.dumps([commit_sha] if commit_sha else []),
                now,
                now,
                now,
            ),
        )
    return get(skill_id)


def matches(project_id: str, query: str, *, trusted_only: bool = True) -> list[dict[str, Any]]:
    """Prior skills relevant to this request, best first.

    `trusted_only` is the default because an untried skill is a guess, and a
    guess presented as precedent is worse than no precedent at all.
    """
    tokens = _tokens(query)
    if not tokens:
        return []
    statuses = ("active",) if trusted_only else ("active", "proposed")
    found = []
    for skill in _all(project_id):
        if skill["status"] not in statuses:
            continue
        score = _similarity(tokens, set(skill.get("trigger_tokens") or []))
        if score < MATCH_FLOOR:
            continue
        found.append({**skill, "match": round(score, 3)})
    found.sort(key=lambda item: (item["match"], item["confidence"]), reverse=True)
    return found[:MAX_INJECTED]


def record_use(skill_ids: list[str], *, succeeded: bool) -> None:
    """Update trust after a skill was actually used.

    This is the pruning the library depends on: a skill that keeps preceding
    failures retires itself rather than waiting for someone to notice.
    """
    now = utcnow()
    for skill_id in skill_ids:
        skill = get(skill_id)
        if not skill:
            continue
        successes = int(skill["successes"]) + (1 if succeeded else 0)
        failures = int(skill["failures"]) + (0 if succeeded else 1)
        uses = int(skill["uses"]) + 1
        status = skill["status"]
        retired_reason = skill["retired_reason"]
        if failures > successes:
            status = "retired"
            retired_reason = f"Failed {failures} of {uses} times it was applied."
        elif successes >= TRUST_THRESHOLD and status == "proposed":
            status = "active"
        with connect() as conn:
            conn.execute(
                "UPDATE learned_skills SET uses=?, successes=?, failures=?, confidence=?,"
                " status=?, retired_reason=?, updated_at=?, last_used_at=? WHERE id=?",
                (
                    uses,
                    successes,
                    failures,
                    _confidence(successes, failures),
                    status,
                    retired_reason,
                    now,
                    now,
                    skill_id,
                ),
            )


def get(skill_id: str) -> dict[str, Any] | None:
    found = rows("SELECT * FROM learned_skills WHERE id=?", (skill_id,))
    return _shape(decode(found[0])) if found else None


def list_skills(
    workspace_id: str, project_id: str = "", status: str = "", limit: int = 100
) -> list[dict[str, Any]]:
    where = "workspace_id=?"
    params: tuple[Any, ...] = (workspace_id,)
    if project_id:
        where += " AND project_id=?"
        params += (project_id,)
    if status:
        where += " AND status=?"
        params += (status,)
    return [
        _shape(decode(item))
        for item in rows(
            f"SELECT * FROM learned_skills WHERE {where}"
            " ORDER BY confidence DESC, updated_at DESC LIMIT ?",
            (*params, max(1, min(int(limit), 500))),
        )
    ]


def retire(skill_id: str, reason: str = "Retired by a reviewer.") -> dict[str, Any] | None:
    """Manual pruning. The librarian is a person as well as a rule."""
    with connect() as conn:
        conn.execute(
            "UPDATE learned_skills SET status='retired', retired_reason=?, updated_at=?"
            " WHERE id=?",
            (reason[:500], utcnow(), skill_id),
        )
    return get(skill_id)


def as_prompt_section(skills: list[dict[str, Any]]) -> str:
    """Render precedents for an agent prompt, with the evidence that earned them."""
    if not skills:
        return ""
    blocks = []
    for skill in skills:
        proof = f"{skill['successes']} time{'s' if skill['successes'] != 1 else ''}"
        files = ", ".join(skill["files"][:4])
        block = f"- {skill['trigger']} (worked {proof})"
        if files:
            block += f"\n  Files last time: {files}"
        if skill.get("approach"):
            block += f"\n  What was done: {skill['approach'][:300]}"
        blocks.append(block)
    return (
        "\nHow this company has done this before — treat as precedent, not "
        "instruction, and check it still applies:\n" + "\n".join(blocks)
    )


def _all(project_id: str) -> list[dict[str, Any]]:
    return [
        _shape(decode(item))
        for item in rows("SELECT * FROM learned_skills WHERE project_id=?", (project_id,))
    ]


def _closest(project_id: str, tokens: set[str], *, threshold: float) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for skill in _all(project_id):
        if skill["status"] == "retired":
            continue
        score = _similarity(tokens, set(skill.get("trigger_tokens") or []))
        if score >= threshold and score > best_score:
            best, best_score = skill, score
    return best


def _reinforce(
    skill: dict[str, Any],
    files: list[str],
    run_id: str,
    context_event_id: str,
    commit_sha: str,
) -> dict[str, Any] | None:
    successes = int(skill["successes"]) + 1
    uses = int(skill["uses"]) + 1
    # A second independent success is what turns a coincidence into a skill.
    status = "active" if successes >= TRUST_THRESHOLD else skill["status"]
    now = utcnow()
    with connect() as conn:
        conn.execute(
            "UPDATE learned_skills SET uses=?, successes=?, confidence=?, status=?,"
            " files_json=?, run_ids_json=?, context_ids_json=?, commits_json=?,"
            " updated_at=?, last_used_at=? WHERE id=?",
            (
                uses,
                successes,
                _confidence(successes, int(skill["failures"])),
                status,
                json.dumps(_merge(skill["files"], files, 12)),
                json.dumps(_merge(skill["run_ids"], [run_id], 20)),
                json.dumps(_merge(skill["context_ids"], [context_event_id], 20)),
                json.dumps(_merge(skill["commits"], [commit_sha], 20)),
                now,
                now,
                skill["id"],
            ),
        )
    return get(skill["id"])


def _shape(skill: dict[str, Any]) -> dict[str, Any]:
    for key in ("files", "run_ids", "context_ids", "commits", "trigger_tokens"):
        skill[key] = skill.get(key) or []
    return skill


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall(str(text or "").casefold())
        if token not in STOP_WORDS and len(token) > 1
    }


def _similarity(left: set[str], right: set[str]) -> float:
    """Jaccard overlap. Symmetric, bounded, and trivial to explain in a review."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _confidence(successes: int, failures: int) -> float:
    """Laplace-smoothed success rate, so one lucky run cannot report certainty."""
    return round((successes + 1) / (successes + failures + 2), 4)


def _merge(existing: list[str], new: list[str], limit: int) -> list[str]:
    return list(dict.fromkeys([*existing, *[item for item in new if item]]))[:limit]


def _name(task: str) -> str:
    cleaned = " ".join(str(task or "").split())
    return (cleaned[:70] + "…") if len(cleaned) > 70 else cleaned or "Untitled skill"
