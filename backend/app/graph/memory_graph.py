from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.core.config import settings

from .arcadedb_store import ArcadeDBGraphStore, rank_records
from .base import GraphEvidence, GraphStore
from .schema import EDGE_TYPES, PROJECT_SCOPED_VERTEX_TYPES, VERTEX_TYPES


class InMemoryGraphStore(GraphStore):
    """Test-only graph implementation with the same contract as ArcadeDB."""

    def __init__(self):
        self.vertices: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        self.edges: list[dict[str, str]] = []

    def health(self) -> dict[str, Any]:
        return {
            "backend": "memory",
            "connected": True,
            "database": "test",
            "node_counts": self.node_counts(),
            "edge_counts": self.edge_counts(),
        }

    def initialize(self) -> None:
        return None

    def _put(self, kind: str, value: dict[str, Any]) -> None:
        self.vertices[kind][value["id"]] = dict(value)

    def upsert_node(self, node_type: str, payload: dict[str, Any]) -> None:
        if node_type not in VERTEX_TYPES:
            raise ValueError(f"Unsupported graph node type: {node_type}")
        self._put(node_type, payload)

    def upsert_project(self, project: dict[str, Any]) -> None:
        self._put("Project", project)

    def upsert_repository(self, repository: dict[str, Any]) -> None:
        self._put("Repository", repository)

    def upsert_service(self, service: dict[str, Any]) -> None:
        self._put("Service", service)

    def upsert_file(self, file: dict[str, Any]) -> None:
        self._put("File", file)

    def upsert_issue(self, issue: dict[str, Any]) -> None:
        self._put("Issue", issue)

    def upsert_pull_request(self, pull_request: dict[str, Any]) -> None:
        self._put("PullRequest", pull_request)

    def upsert_slack_channel(self, channel: dict[str, Any]) -> None:
        self._put("SlackChannel", channel)

    def upsert_slack_message(self, message: dict[str, Any]) -> None:
        self._put("SlackMessage", message)

    def upsert_evidence_source(self, source: dict[str, Any]) -> None:
        self._put("EvidenceSource", source)

    def upsert_runbook_step(self, step: dict[str, Any]) -> None:
        self._put("RunbookStep", step)

    def upsert_agent_action(self, action: dict[str, Any]) -> None:
        self._put("AgentAction", action)

    def upsert_operational_assertion(self, assertion: dict[str, Any]) -> None:
        self._put("OperationalAssertion", assertion)

    def upsert_change_impact(self, impact: dict[str, Any]) -> None:
        self._put("ChangeImpact", impact)

    def clear_repository_knowledge(self, project_id: str) -> None:
        removed: set[str] = set()
        repository_sources = {"repo_file", "github_issue", "pull_request"}
        for kind in ("KnowledgeChunk", "KnowledgeItem"):
            for vertex_id, value in list(self.vertices[kind].items()):
                if (
                    value.get("project_id") == project_id
                    and value.get("source_type") in repository_sources
                ):
                    removed.add(vertex_id)
                    del self.vertices[kind][vertex_id]
        for kind in (
            "File",
            "Issue",
            "PullRequest",
            "Directory",
            "Package",
            "Service",
            "EnvironmentVariable",
            "ConfigKey",
            "DockerService",
            "Workflow",
            "Job",
            "Step",
            "Script",
            "Command",
            "Endpoint",
            "Function",
            "Class",
            "Module",
            "Import",
            "Label",
            "User",
            "Comment",
            "LogLine",
            "ErrorPattern",
            "ContextWindow",
        ):
            for vertex_id, value in list(self.vertices[kind].items()):
                if value.get("project_id") == project_id:
                    removed.add(vertex_id)
                    del self.vertices[kind][vertex_id]
        self.edges = [
            edge
            for edge in self.edges
            if edge["from_id"] not in removed and edge["to_id"] not in removed
        ]

    def upsert_knowledge_item(self, item: dict[str, Any]) -> None:
        self._put("KnowledgeItem", item)

    def upsert_chunk(self, chunk: dict[str, Any]) -> None:
        self._put("KnowledgeChunk", chunk)

    def upsert_runbook(self, runbook: dict[str, Any]) -> None:
        self._put("Runbook", runbook)

    def link(self, edge_type: str, from_type: str, from_id: str, to_type: str, to_id: str) -> None:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"Unsupported graph edge type: {edge_type}")
        edge = {
            "relationship": edge_type,
            "from_type": from_type,
            "from_id": from_id,
            "to_type": to_type,
            "to_id": to_id,
        }
        if edge not in self.edges:
            self.edges.append(edge)

    def retrieve_context(
        self, project_id: str, query: str, service_name: str | None = None, limit: int = 12
    ) -> list[GraphEvidence]:
        records = [
            value
            for value in self.vertices["KnowledgeChunk"].values()
            if value.get("project_id") == project_id
        ]
        return rank_records(records, query, service_name, limit)

    def get_retrieval_trace(self, project_id: str, chunk_ids: list[str]) -> list[dict[str, Any]]:
        return [
            edge
            for edge in self.edges
            if edge["from_id"] in chunk_ids or edge["to_id"] in chunk_ids
        ]

    def node_counts(self, project_id: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for kind, values in self.vertices.items():
            if project_id:
                scoped = {
                    key: value
                    for key, value in values.items()
                    if value.get("project_id") == project_id
                    or (kind == "Project" and value.get("id") == project_id)
                }
                count = len(scoped)
            else:
                count = len(values)
            if count:
                counts[kind] = count
        return dict(sorted(counts.items()))

    def edge_counts(self, project_id: str | None = None) -> dict[str, int]:
        edges = self.list_edges(project_id, limit=1_000_000) if project_id else self.edges
        counts: dict[str, int] = {}
        for edge in edges:
            counts[edge["relationship"]] = counts.get(edge["relationship"], 0) + 1
        return dict(sorted(counts.items()))

    def graph_summary(self, project_id: str) -> dict[str, Any]:
        nodes = self.node_counts(project_id)
        edges = self.edge_counts(project_id)
        return {
            "project_id": project_id,
            "node_counts": nodes,
            "edge_counts": edges,
            "total_nodes": sum(nodes.values()),
            "total_edges": sum(edges.values()),
            "services": self.list_nodes(project_id, "Service", 100),
            "files": self.list_nodes(project_id, "File", 200),
        }

    def list_nodes(
        self, project_id: str, node_type: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        types = [node_type] if node_type else PROJECT_SCOPED_VERTEX_TYPES
        output: list[dict[str, Any]] = []
        for kind in types:
            if not kind:
                continue
            for value in self.vertices[kind].values():
                if value.get("project_id") == project_id or (
                    kind == "Project" and value.get("id") == project_id
                ):
                    output.append({"node_type": kind, **value})
                    if len(output) >= limit:
                        return output
        return output

    def list_edges(
        self, project_id: str, edge_type: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        project_node_ids = {
            value["id"]
            for kind in PROJECT_SCOPED_VERTEX_TYPES
            for value in self.vertices[kind].values()
            if value.get("project_id") == project_id
            or (kind == "Project" and value.get("id") == project_id)
        }
        output = [
            edge
            for edge in self.edges
            if (not edge_type or edge["relationship"] == edge_type)
            and (edge["from_id"] in project_node_ids or edge["to_id"] in project_node_ids)
        ]
        return output[:limit]

    def service_graph(self, project_id: str, service_name: str) -> dict[str, Any]:
        service_id = f"{project_id}:{service_name}"
        edges = [
            edge
            for edge in self.list_edges(project_id, limit=1000)
            if service_id in {edge["from_id"], edge["to_id"]}
        ]
        return {
            "project_id": project_id,
            "service_name": service_name,
            "nodes": [
                node
                for node in self.list_nodes(project_id, limit=1000)
                if node.get("id") == service_id or node.get("name") == service_name
            ],
            "edges": edges,
            "evidence": [
                {
                    "chunk_id": item.chunk_id,
                    "source_type": item.source_type,
                    "source_title": item.source_title,
                    "source_url": item.source_url,
                    "snippet": item.text[:360],
                    "confidence": item.metadata.get("retrieval_confidence", 0),
                }
                for item in self.retrieve_context(project_id, service_name, service_name)
            ],
        }

    def file_graph(self, project_id: str, path: str) -> dict[str, Any]:
        file_id = f"file:{project_id}:{path}"
        return {
            "project_id": project_id,
            "path": path,
            "nodes": [
                node
                for node in self.list_nodes(project_id, "File", 500)
                if node.get("id") == file_id or node.get("path") == path
            ],
            "edges": [
                edge
                for edge in self.list_edges(project_id, limit=1000)
                if file_id in {edge["from_id"], edge["to_id"]}
            ],
        }

    def reset(self) -> None:
        self.vertices.clear()
        self.edges.clear()


_store: GraphStore | None = None


def get_graph_store() -> GraphStore:
    global _store
    if _store is None:
        _store = (
            InMemoryGraphStore() if settings.graph_backend == "memory" else ArcadeDBGraphStore()
        )
    return _store


def set_graph_store(store: GraphStore) -> None:
    global _store
    _store = store
