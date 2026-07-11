from dataclasses import dataclass, field
from typing import Any


@dataclass
class RouteResult:
    domain: str
    subdomain: str
    context_window: str
    query_type: str
    service_name: str | None
    boundary_type: str
    confidence: float


@dataclass
class HCAGTrace:
    domain: str
    subdomain: str
    context_window: str
    boundary_type: str
    query_type: str
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    graph_paths: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    engine: str = "hcag"
