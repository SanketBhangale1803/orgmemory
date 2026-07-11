from __future__ import annotations


class FallbackPlanner:
    def classify(self, query: str) -> str:
        lowered = query.lower()
        if any(term in lowered for term in ("why", "root cause", "relationship", "because")):
            return "multi_hop"
        if any(term in lowered for term in ("when", "before", "after", "recent")):
            return "temporal"
        return "single_hop"
