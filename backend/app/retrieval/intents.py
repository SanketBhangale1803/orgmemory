from __future__ import annotations

import re

REPOSITORY_REFERENCE_RE = re.compile(
    r"\b(?:repo|repository|project|codebase|github\s+repo(?:sitory)?)\b",
    re.IGNORECASE,
)
OWNERSHIP_QUESTION_RE = re.compile(
    r"\b(?:"
    r"who\s+(?:is|are)\s+(?:the\s+)?(?:owner|maintainer)"
    r"|who\s+owns"
    r"|who\s+is\s+responsible\s+for"
    r"|(?:owner|maintainer|ownership)\s+of"
    r"|(?:repo|repository|project|codebase)\s+(?:owner|maintainer|ownership)"
    r")\b",
    re.IGNORECASE,
)


def ownership_scope(query: str) -> str:
    """Classify the ownership subject without inferring the owner."""

    if not OWNERSHIP_QUESTION_RE.search(query):
        return ""
    return "repository" if REPOSITORY_REFERENCE_RE.search(query) else "entity"
