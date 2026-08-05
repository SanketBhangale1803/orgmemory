from __future__ import annotations

from typing import Any

from app.connectors.slack import SlackConnector
from app.core.database import connect, rows
from app.graph.base import GraphStore

from .safety import sanitize_for_index
from .service import IngestionService


class SlackIngestor:
    def __init__(
        self, ingestion: IngestionService, graph: GraphStore, slack: SlackConnector | None = None
    ):
        self.ingestion = ingestion
        self.graph = graph
        self.slack = slack or SlackConnector()

    def ingest_channel(
        self,
        project_id: str,
        channel_id: str,
        limit: int = 200,
        team_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        channel, messages = self.slack.history(channel_id, limit)
        channel_vertex_id = f"slack-channel:{channel_id}"
        channel_name = channel.get("name", channel_id)
        self.graph.upsert_slack_channel(
            {
                "id": channel_vertex_id,
                "project_id": project_id,
                "name": channel_name,
                "external_id": channel_id,
            }
        )
        count = chunks = created = unchanged = 0
        seen_sources: set[str] = set()
        for message in messages:
            text = (message.get("text") or "").strip()
            if not text:
                continue
            ts = message.get("ts", "unknown")
            source_id = f"slack-message:{channel_id}:{ts}"
            if source_id in seen_sources:
                continue
            seen_sources.add(source_id)
            url = self.slack.permalink(channel_id, ts)
            sanitized_text = sanitize_for_index(text, url)[0]
            existing = rows(
                "SELECT id,content FROM knowledge_items WHERE project_id=? AND source_type IN ('slack','slack_export') AND source_id=?",
                (project_id, source_id),
            )
            count += 1
            if len(existing) == 1 and existing[0]["content"] == sanitized_text:
                unchanged += 1
                continue
            if existing:
                self.graph.delete_source_knowledge(project_id, source_id, "slack")
                with connect() as conn:
                    conn.execute(
                        "DELETE FROM knowledge_items WHERE project_id=? AND source_id=?",
                        (project_id, source_id),
                    )
            result = self.ingestion.ingest_item(
                project_id,
                "slack",
                f"#{channel_name} at {ts}",
                text,
                url,
                source_id,
                {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "user": message.get("user", ""),
                    "timestamp": ts,
                    "team_ids": team_ids or [],
                },
            )
            self.graph.link(
                "SERVICE_MENTIONED_IN", "SlackChannel", channel_vertex_id, "SlackMessage", source_id
            )
            created += 1
            chunks += result["chunks_created"]
        return {
            "project_id": project_id,
            "channel": channel_name,
            "messages_scanned": count,
            "knowledge_items_created": created,
            "knowledge_chunks_created": chunks,
            "sources_unchanged": unchanged,
            "status": "success",
        }
