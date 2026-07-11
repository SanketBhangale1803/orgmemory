from __future__ import annotations

from typing import Any

from app.connectors.slack import SlackConnector
from app.graph.base import GraphStore

from .service import IngestionService


class SlackIngestor:
    def __init__(
        self, ingestion: IngestionService, graph: GraphStore, slack: SlackConnector | None = None
    ):
        self.ingestion = ingestion
        self.graph = graph
        self.slack = slack or SlackConnector()

    def ingest_channel(self, project_id: str, channel_id: str, limit: int = 200) -> dict[str, Any]:
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
        count = chunks = 0
        for message in messages:
            text = (message.get("text") or "").strip()
            if not text:
                continue
            ts = message.get("ts", "unknown")
            source_id = f"slack-message:{channel_id}:{ts}"
            url = self.slack.permalink(channel_id, ts)
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
                },
            )
            self.graph.link(
                "SERVICE_MENTIONED_IN", "SlackChannel", channel_vertex_id, "SlackMessage", source_id
            )
            count += 1
            chunks += result["chunks_created"]
        return {
            "project_id": project_id,
            "channel": channel_name,
            "messages_scanned": count,
            "knowledge_chunks_created": chunks,
            "status": "success",
        }
