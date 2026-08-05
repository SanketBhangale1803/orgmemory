from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SERVICE_RE = re.compile(
    r"\b([a-zA-Z][\w-]*(?:_service|-service|-gateway|-worker|-engine|-ledger|-client|-parser))\b",
    re.IGNORECASE,
)
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
        value.casefold()
        for value in re.findall(
            r"(?im)^\s*(?:SERVICE_NAME\s*=\s*)?[\"'`]([a-z][a-z0-9]*(?:[-_][a-z0-9]+)*(?:"
            r"service|gateway|worker|engine|ledger|client|parser))[\"'`]\s*,?\s*$",
            content[:100_000],
        )
    )
    for raw in content[:100_000].splitlines():
        if not raw.strip().startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in raw.strip().strip("|").split("|")]
        if cells and SERVICE_RE.fullmatch(cells[0]):
            values.add(cells[0].casefold())
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
    return sorted(values)[:50]


def extract_signals(content: str) -> dict[str, list[str]]:
    return {
        "errors": [line.strip() for line in ERROR_RE.findall(content)[:30]],
        "commands": [line.strip() for line in COMMAND_RE.findall(content)[:30]],
        "procedures": [line.strip() for line in PROCEDURE_RE.findall(content)[:50]],
        "approvers": [value.strip() for value in APPROVER_RE.findall(content)[:20]],
    }


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    line_start: int
    line_end: int
    token_count: int
    section: str


TOKEN_COUNT_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SECTION_RE = re.compile(
    r"^\s*(?:#{1,6}\s+.+|(?:async\s+)?(?:def|class|function)\s+[A-Za-z_$][\w$]*|"
    r"(?:export\s+)?(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=|[A-Za-z][^:]{1,80}:\s*)$"
)


def _token_count(text: str) -> int:
    return len(TOKEN_COUNT_RE.findall(text))


def chunk_document(
    content: str, target_tokens: int = 520, overlap_tokens: int = 80
) -> list[DocumentChunk]:
    """Create line-addressable, context-preserving chunks (normally 300-800 tokens)."""
    lines = content.splitlines()
    if not any(line.strip() for line in lines):
        return []
    chunks: list[DocumentChunk] = []
    start = 0
    section = ""
    while start < len(lines):
        while start < len(lines) and not lines[start].strip():
            start += 1
        if start >= len(lines):
            break
        for index in range(start, -1, -1):
            if SECTION_RE.match(lines[index].strip()):
                section = lines[index].strip()[:160]
                break
        total = 0
        end = start
        last_boundary: int | None = None
        while end < len(lines):
            total += _token_count(lines[end]) + 1
            if (not lines[end].strip() or SECTION_RE.match(lines[end].strip())) and total >= 300:
                last_boundary = end
            end += 1
            if total >= target_tokens:
                if last_boundary is not None and total >= 420:
                    end = max(start + 1, last_boundary)
                break
            if total >= 780:
                break
        text = "\n".join(lines[start:end]).strip()
        if text:
            chunks.append(
                DocumentChunk(
                    text=text,
                    line_start=start + 1,
                    line_end=end,
                    token_count=_token_count(text),
                    section=section,
                )
            )
        if end >= len(lines):
            break
        overlap = 0
        next_start = end
        while next_start > start + 1 and overlap < overlap_tokens:
            next_start -= 1
            overlap += _token_count(lines[next_start]) + 1
        start = next_start
    return chunks


def chunk_text(content: str, size: int = 520, overlap: int = 80) -> list[str]:
    """Compatibility wrapper; size and overlap are token targets."""
    return [chunk.text for chunk in chunk_document(content, size, overlap)]
