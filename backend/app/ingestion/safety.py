from __future__ import annotations

import re
from typing import Any

SECRET_NAME_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|bearer|client[_-]?secret|"
    r"credential|database[_-]?(?:url|password)|github[_-]?token|jwt[_-]?secret|"
    r"openai[_-]?api[_-]?key|password|private[_-]?key|secret|slack[_-]?token)"
)
ENV_ASSIGNMENT_RE = re.compile(
    r"(?m)^(?P<prefix>\s*(?:export\s+)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*)(?P<value>[^\n#]*)(?P<comment>\s*(?:#.*)?)$"
)
KEY_VALUE_RE = re.compile(
    r"(?im)(?P<prefix>[\"']?(?P<name>[A-Za-z_][A-Za-z0-9_.-]*)[\"']?\s*[:=]\s*[\"'])(?P<value>[^\"'\n]{4,})(?P<suffix>[\"'])"
)
TOKEN_PATTERNS = (
    re.compile(r"\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[opsu]_[A-Za-z0-9]{20,})\b"),
    re.compile(r"\b(?:sk|rk|rbk)-?[A-Za-z0-9_-]{20,}\b", re.IGNORECASE),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{16,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
)
PEM_RE = re.compile(r"-----BEGIN [^-]+-----.*?-----END [^-]+-----", re.DOTALL)
URL_CREDENTIAL_RE = re.compile(r"(?P<scheme>https?://)(?P<credentials>[^/@\s:]+:[^/@\s]+)@")


def _is_env_schema(source_ref: str) -> bool:
    name = source_ref.rsplit("/", 1)[-1].casefold()
    return name == ".env.example" or name.startswith(".env.") or name.endswith(".env.example")


def sanitize_for_index(content: str, source_ref: str = "") -> tuple[str, int]:
    """Remove credentials before content reaches SQLite, ArcadeDB, logs, or embeddings."""
    redactions = 0

    def replace_env(match: re.Match[str]) -> str:
        nonlocal redactions
        name = match.group("name")
        value = match.group("value").strip()
        if not value or (not _is_env_schema(source_ref) and not SECRET_NAME_RE.search(name)):
            return match.group(0)
        redactions += 1
        return f"{match.group('prefix')}<redacted>{match.group('comment')}"

    sanitized = ENV_ASSIGNMENT_RE.sub(replace_env, content)

    def replace_key_value(match: re.Match[str]) -> str:
        nonlocal redactions
        if not SECRET_NAME_RE.search(match.group("name")):
            return match.group(0)
        redactions += 1
        return f"{match.group('prefix')}<redacted>{match.group('suffix')}"

    sanitized = KEY_VALUE_RE.sub(replace_key_value, sanitized)
    sanitized, count = PEM_RE.subn("<redacted-private-key>", sanitized)
    redactions += count
    sanitized, count = URL_CREDENTIAL_RE.subn(r"\g<scheme><redacted>@", sanitized)
    redactions += count
    for pattern in TOKEN_PATTERNS:
        sanitized, count = pattern.subn("<redacted-token>", sanitized)
        redactions += count
    return sanitized, redactions


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_for_index(value)[0]
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, dict):
        return {
            key: (
                "<redacted>"
                if key != "secret_redactions" and SECRET_NAME_RE.search(str(key))
                else sanitize_metadata(item)
            )
            for key, item in value.items()
        }
    return value


def contains_secret_material(content: str) -> bool:
    if PEM_RE.search(content) or URL_CREDENTIAL_RE.search(content):
        return True
    return any(pattern.search(content) for pattern in TOKEN_PATTERNS)
