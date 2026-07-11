from __future__ import annotations

from .migrations import EDGE_TYPES, VERTEX_TYPES

PROJECT_SCOPED_VERTEX_TYPES = [
    name for name in VERTEX_TYPES if name not in {"Organization", "Language", "Dependency"}
]

__all__ = ["EDGE_TYPES", "PROJECT_SCOPED_VERTEX_TYPES", "VERTEX_TYPES"]
