"""Carry the thread forward, so a chat behaves like a conversation.

Every other lane in this package answers one question in isolation. That is the
right shape for an API and the wrong shape for a chat window, where people speak
the way they speak to a colleague: the first message sets the subject and every
message after it points back at that subject with a pronoun.

    > the checkout service keeps 502ing
    > why is it failing?

Answered statelessly, the second question has no subject at all. Retrieval still
returns *something* — every corpus contains an incident — so the failure is not
an error but a confident answer about the wrong thing, which is the worst outcome
this system can produce. It looks exactly like knowledge.

So this module does two jobs, in this order:

* **Resolve** — rewrite a follow-up against what was already said, so "why is it
  failing" searches for the subject the asker actually has in mind.
* **Refuse to resolve** — when the reference points at nothing, because the
  window opened on it, say so and ask. A question whose subject is unknown cannot
  be answered by looking harder.

The rewrite is deliberately conservative and deterministic. It only ever *adds*
the recovered subject to the query, and only when a reference word is present
with nothing in the sentence to bind it to. It cannot invent a subject, and if
the guess is poor the cost is a slightly wider search rather than a wrong answer
delivered with confidence.
"""

from __future__ import annotations

import re
from typing import Any

# How far back to look. Subjects go stale: in a long thread the thing "it" refers
# to is nearly always from the last few exchanges, and reaching further back
# reliably recovers the wrong noun.
LOOKBACK_TURNS = 6
# Longest subject worth carrying forward. Past this the phrase is a sentence
# rather than a subject, and appending it buries the actual question.
MAX_SUBJECT_WORDS = 12

# A reference word standing where a subject should be. Matched at word level so
# "it" matches and "item" does not.
#
# "this" and "these" are deliberately absent. They are nearly always determiners
# pointing at the project in hand — "how do I run this locally", "if I change
# this API" — and the project is never unknown, because one is always selected.
# Treating them as dangling would interrogate people about questions that were
# perfectly clear, which is its own failure mode.
REFERENCE_RE = re.compile(
    r"\b(it|its|it's|that|those|them|they|the same|same one|the latter|the former)\b",
    re.IGNORECASE,
)
# A reference only lacks a subject when it stands *as* the subject. Late in a
# sentence it almost always points back within that same sentence — "which
# technology holds records, and where is that configured" is self-contained — so
# only an early reference in a short question counts.
SUBJECT_POSITION_WORDS = 4
MAX_QUERY_WORDS = 10

# Something concrete in the sentence for a reference word to attach to. If the
# asker named a service, a file, a repository, or any specific noun, the sentence
# stands on its own and must not be rewritten.
SUBJECT_PRESENT_RE = re.compile(
    r"\b[\w-]+\.(?:py|ts|tsx|js|jsx|go|rs|java|rb|css|scss|html|yml|yaml|json|toml|md|sql)\b"
    r"|\b\w+[-_](?:service|api|worker|job|queue|db|server|app|ui|client)\b"
    r"|\b(?:service|repo|repository|project|pipeline|deploy|build|test|endpoint|"
    r"page|component|branch|pr|issue|ticket|migration|schema|table|queue|job|"
    r"cluster|container|pod|workflow|script|module|package|function|class)\b"
    r"|@\w+|#[\w-]+|\b[A-Z]{2,}-\d+\b"
    r"|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b",
    re.IGNORECASE,
)

# Words that never make a useful search subject on their own.
_STOP = {
    "a",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "so",
    "that",
    "the",
    "then",
    "there",
    "these",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "you",
    "your",
}


def resolve(query: str, history: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Bind a follow-up to what came before it.

    Returns the query to actually search with, the subject recovered (if any),
    and whether a reference was left dangling with nothing to bind it to.
    """
    clean = (query or "").strip()
    result: dict[str, Any] = {"query": clean, "subject": "", "dangling": False}
    if not clean or not _needs_resolution(clean):
        return result

    subject = _recent_subject(history or [])
    if not subject:
        # The window opened on a pronoun. No amount of retrieval fixes this.
        result["dangling"] = True
        return result

    result["subject"] = subject
    result["query"] = f"{clean} ({subject})"
    return result


def _needs_resolution(query: str) -> bool:
    """True when the sentence leans on a reference word and names nothing itself."""
    words = re.findall(r"[\w'’./#@-]+", query)
    if len(words) > MAX_QUERY_WORDS:
        # A long question carries its own context; a reference inside it points
        # at a noun the same sentence already supplied.
        return False
    opening = " ".join(words[:SUBJECT_POSITION_WORDS])
    if not REFERENCE_RE.search(opening):
        return False
    # "is this repo failing" carries its own subject; only a bare reference counts.
    return not SUBJECT_PRESENT_RE.search(query)


def _recent_subject(history: list[dict[str, Any]]) -> str:
    """Recover the most recent thing the thread was about.

    Only the asker's own turns anchor a reference. An assistant turn is prose
    about a subject rather than a statement of one — mining it yields the nouns
    of an explanation ("need", "know", "mean") or, worse, a related file that was
    mentioned once and was never what the person had in mind. Coming back empty
    and asking is strictly better than either.
    """
    turns = [
        turn
        for turn in history[-LOOKBACK_TURNS:]
        if isinstance(turn, dict)
        and str(turn.get("content") or "").strip()
        and str(turn.get("role") or "").lower() == "user"
    ]
    for turn in reversed(turns):
        subject = _subject_of(str(turn["content"]))
        if subject:
            return subject
    return ""


def _subject_of(text: str) -> str:
    """Reduce a turn to the words worth searching for."""
    body = text.strip()
    if _needs_resolution(body):
        # That turn was itself a bare reference; it cannot anchor this one.
        return ""
    words = [word for word in re.findall(r"[\w./#@-]+", body) if word.lower() not in _STOP]
    if not words:
        return ""
    return " ".join(words[:MAX_SUBJECT_WORDS])


def unresolved_reference(query: str) -> dict[str, Any]:
    """The clarification for a reference that points at nothing.

    Phrased so it reads as attention rather than incapacity: the system is not
    saying it lacks memory, it is saying this sentence has no subject yet.
    """
    referent = _first_reference(query) or "it"
    return {
        "reason": "unresolved_reference",
        "question": f"What does “{referent}” refer to?",
        "detail": (
            f"This is the first message in the thread, so I don't know what "
            f"“{referent}” points at yet. I could search for something plausible "
            "and answer confidently about the wrong thing — naming it costs you a "
            "few words and gets you the right answer."
        ),
        "options": [
            {"label": "A service or repository", "hint": 'e.g. "why is checkout-api failing?"'},
            {"label": "A recent change", "hint": 'e.g. "why is last night’s deploy failing?"'},
            {"label": "Something you were just looking at", "hint": "paste the error or the name"},
        ],
    }


def _first_reference(query: str) -> str:
    match = REFERENCE_RE.search(query or "")
    return match.group(0).lower() if match else ""
