from __future__ import annotations

import re
from pathlib import Path

SERVICE_RE = re.compile(r"\b([a-zA-Z][\w-]*(?:_service|-service))\b", re.IGNORECASE)
NON_SERVICE_HOSTS = {
    "localhost",
    "http",
    "https",
    "width",
    "height",
    "font-weight",
    "line-height",
    "margin",
    "padding",
    "top",
    "left",
    "right",
    "bottom",
    "border-radius",
}
ERROR_RE = re.compile(
    r"(?im)^.*(?:error|exception|failed|timeout|unreachable|refused|root cause|caused by).*$"
)
COMMAND_RE = re.compile(
    r"(?m)^(?:\$\s*)?((?:docker|kubectl|helm|systemctl|npm|yarn|pip|python|make|git|curl|aws|gcloud|az|jenkins)\s+[^\n]+)$"
)
PROCEDURE_RE = re.compile(r"(?m)^\s*(?:\d+[.)]|[-*])\s+(.{8,300})$")
APPROVER_RE = re.compile(
    r"(?i)\b(?:approved? by|requires? approval from|owner:)\s*([A-Za-z][A-Za-z ._-]{1,80})"
)


def extract_services(content: str, source_ref: str = "") -> list[str]:
    values = {value.lower() for value in SERVICE_RE.findall(content[:100_000])}
    values.update(
        value.lower()
        for value in re.findall(r"\b([a-z][\w-]+):\d{2,5}\b", content[:100_000])
        if value.lower() not in NON_SERVICE_HOSTS
    )
    for part in Path(source_ref).parts:
        if part.lower().endswith(("_service", "-service")):
            values.add(part.lower())
    source_lower = source_ref.lower()
    compose = re.search(r"(?ms)^services:\s*\n(.*?)(?:^\S|\Z)", content)
    if compose and source_lower.endswith((".yml", ".yaml")):
        values.update(re.findall(r"(?m)^\s{2}([A-Za-z][\w-]+):\s*$", compose.group(1)))
    normalized = {
        value.removesuffix("-service") + "_service" if value.endswith("-service") else value
        for value in values
    }
    return sorted(normalized)[:50]


def extract_signals(content: str) -> dict[str, list[str]]:
    return {
        "errors": [line.strip() for line in ERROR_RE.findall(content)[:30]],
        "commands": [line.strip() for line in COMMAND_RE.findall(content)[:30]],
        "procedures": [line.strip() for line in PROCEDURE_RE.findall(content)[:50]],
        "approvers": [value.strip() for value in APPROVER_RE.findall(content)[:20]],
    }


def chunk_text(content: str, size: int = 1600, overlap: int = 200) -> list[str]:
    text = content.strip()
    if not text:
        return []
    chunks: list[str] = []
    cursor = 0
    while cursor < len(text):
        end = min(len(text), cursor + size)
        if end < len(text):
            split = max(text.rfind("\n", cursor, end), text.rfind(". ", cursor, end))
            if split > cursor + size // 2:
                end = split + 1
        chunks.append(text[cursor:end].strip())
        if end >= len(text):
            break
        cursor = end - overlap
    return chunks
