from __future__ import annotations

from typing import Any

from app.graph.base import GraphStore


class GraphRetriever:
    def __init__(self, graph: GraphStore):
        self.graph = graph

    def summary(self, project_id: str) -> dict[str, Any]:
        return self.graph.graph_summary(project_id)

    def nodes(
        self, project_id: str, node_type: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        return self.graph.list_nodes(project_id, node_type, limit)

    def edges(
        self, project_id: str, edge_type: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        return self.graph.list_edges(project_id, edge_type, limit)

    def service(self, project_id: str, service_name: str) -> dict[str, Any]:
        return self.graph.service_graph(project_id, service_name)

    def file(self, project_id: str, path: str) -> dict[str, Any]:
        return self.graph.file_graph(project_id, path)
