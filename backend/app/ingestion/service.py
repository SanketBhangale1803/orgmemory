from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.audit import AuditService
from app.core.database import connect, new_id, row, utcnow
from app.graph.base import GraphStore
from app.hcag_adapter import HCAGAdapter

from .extractors import chunk_text, extract_services, extract_signals

SOURCE_VERTEX = {
    "repo_file": "File",
    "github_issue": "Issue",
    "pull_request": "PullRequest",
    "slack": "SlackMessage",
    "slack_export": "SlackMessage",
}


class IngestionService:
    def __init__(self, graph: GraphStore, hcag: HCAGAdapter, audit: AuditService | None = None):
        self.graph = graph
        self.hcag = hcag
        self.audit = audit or AuditService()

    def create_project(self, name: str, repository: str = "", project_id: str | None = None) -> str:
        existing = (
            row("SELECT id,created_at FROM projects WHERE repository=?", (repository,))
            if repository and not project_id
            else None
        )
        project_id = project_id or (existing["id"] if existing else new_id("prj"))
        now = utcnow()
        created_at = existing["created_at"] if existing else now
        with connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects VALUES (?,?,?,?,?,?)",
                (project_id, name, repository, "ready", created_at, now),
            )
        self.graph.upsert_project(
            {
                "id": project_id,
                "name": name,
                "repository": repository,
                "created_at": created_at,
                "updated_at": now,
            }
        )
        if repository:
            repository_id = f"repo:{project_id}"
            self.graph.upsert_repository(
                {
                    "id": repository_id,
                    "project_id": project_id,
                    "url": repository,
                    "name": Path(repository).name,
                }
            )
            self.graph.link("PROJECT_HAS_REPO", "Project", project_id, "Repository", repository_id)
        event = "project.reindexed" if existing else "project.created"
        summary = f"Re-indexed project {name}" if existing else f"Created project {name}"
        self.audit.record(event, summary, project_id)
        return project_id

    def ingest_item(
        self,
        project_id: str,
        source_type: str,
        title: str,
        content: str,
        source_url: str = "",
        source_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = dict(metadata or {})
        item_id = new_id("item")
        source_id = source_id or new_id("src")
        services = extract_services(content, source_url)
        signals = extract_signals(content)
        route = self.hcag.ingest_knowledge_item(
            {"project_id": project_id, "source_title": title, "content": content}
        )
        metadata.update({"services": services, "signals": signals, "hcag": route})
        now = utcnow()
        with connect() as conn:
            conn.execute(
                "INSERT INTO knowledge_items VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    project_id,
                    source_type,
                    source_id,
                    title,
                    source_url,
                    content,
                    json.dumps(metadata),
                    now,
                ),
            )
        vertex_type = SOURCE_VERTEX.get(source_type, "EvidenceSource")
        source_payload = {
            "id": source_id,
            "project_id": project_id,
            "title": title,
            "url": source_url,
            "source_type": source_type,
        }
        if vertex_type == "File":
            self.graph.upsert_file(source_payload)
        elif vertex_type == "Issue":
            self.graph.upsert_issue(source_payload)
        elif vertex_type == "PullRequest":
            self.graph.upsert_pull_request(source_payload)
        elif vertex_type == "SlackMessage":
            self.graph.upsert_slack_message(source_payload)
        else:
            self.graph.upsert_evidence_source(source_payload)
        item_payload = {
            "id": item_id,
            "project_id": project_id,
            "source_id": source_id,
            "source_type": source_type,
            "source_title": title,
            "source_url": source_url,
            "content": content,
            "metadata_json": json.dumps(metadata),
            "created_at": now,
        }
        self.graph.upsert_knowledge_item(item_payload)
        self.graph.link(
            "KNOWLEDGE_ITEM_DERIVED_FROM",
            "KnowledgeItem",
            item_id,
            vertex_type,
            source_id,
        )
        chunks = chunk_text(content)
        for index, text in enumerate(chunks):
            chunk_id = new_id("chunk")
            chunk_services = [
                service
                for service in services
                if service.replace("_", " ") in text.lower().replace("_", " ")
            ] or services
            chunk_signals = extract_signals(text)
            chunk_payload = {
                "id": chunk_id,
                "project_id": project_id,
                "item_id": item_id,
                "text": text,
                "source_type": source_type,
                "source_title": title,
                "source_url": source_url,
                "service_names": chunk_services,
                "metadata_json": json.dumps(
                    {
                        "chunk_index": index,
                        "item_id": item_id,
                        "signals": chunk_signals,
                        "hcag": route,
                        "source_version": metadata.get("source_version", ""),
                        "commit_sha": metadata.get("commit_sha", ""),
                        "source_updated_at": metadata.get("source_updated_at", ""),
                    }
                ),
            }
            self.graph.upsert_chunk(chunk_payload)
            self.graph.link(
                "CHUNK_DERIVED_FROM", "KnowledgeChunk", chunk_id, "KnowledgeItem", item_id
            )
            if source_type == "repo_file":
                self.graph.link_file_to_chunk(source_id, chunk_id)
            for service in chunk_services:
                service_id = f"{project_id}:{service}"
                self.graph.upsert_service(
                    {"id": service_id, "project_id": project_id, "name": service}
                )
                self.graph.link("PROJECT_HAS_SERVICE", "Project", project_id, "Service", service_id)
                self.graph.link_chunk_to_service(chunk_id, service_id)
        self.audit.record(
            "knowledge.ingested",
            f"Ingested {title}",
            project_id,
            payload={
                "item_id": item_id,
                "source_type": source_type,
                "chunks": len(chunks),
                "services": services,
            },
        )
        return {
            "item_id": item_id,
            "chunks_created": len(chunks),
            "services": services,
            "signals": signals,
        }
