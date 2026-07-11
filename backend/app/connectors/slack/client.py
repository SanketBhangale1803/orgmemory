from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx

from app.auth import ConnectorSecrets, OAuthStateStore
from app.connectors.base import Connector, ConnectorStatus
from app.core.config import settings


class SlackConnector(Connector):
    def __init__(self, secrets: ConnectorSecrets | None = None):
        self.secrets = secrets or ConnectorSecrets()

    def token(self) -> str | None:
        return settings.slack_bot_token or self.secrets.token("slack")

    def status(self) -> ConnectorStatus:
        accounts = self.secrets.status("slack")
        return ConnectorStatus("slack", True, bool(self.token()), accounts)

    def oauth_url(self, state_store: OAuthStateStore) -> str:
        if not settings.slack_client_id:
            raise ValueError("Slack OAuth is not configured")
        state = state_store.create("slack")
        return "https://slack.com/oauth/v2/authorize?" + urlencode(
            {
                "client_id": settings.slack_client_id,
                "scope": "channels:history,groups:history,channels:read,groups:read,users:read",
                "redirect_uri": settings.slack_redirect_uri,
                "state": state,
            }
        )

    def complete_oauth(self, code: str, state: str, state_store: OAuthStateStore) -> dict:
        state_store.consume("slack", state)
        response = httpx.post(
            "https://slack.com/api/oauth.v2.access",
            auth=(settings.slack_client_id, settings.slack_client_secret),
            data={"code": code, "redirect_uri": settings.slack_redirect_uri},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise ValueError(f"Slack OAuth failed: {data.get('error')}")
        team = data["team"]
        self.secrets.save(
            "slack",
            team["id"],
            team["name"],
            data["access_token"],
            {"scope": data.get("scope", "")},
        )
        return {"workspace": team["name"]}

    def list_channels(self) -> list[dict[str, Any]]:
        return self._api(
            "conversations.list", {"types": "public_channel,private_channel", "limit": 200}
        ).get("channels", [])

    def history(self, channel_id: str, limit: int) -> tuple[dict, list[dict]]:
        info = self._api("conversations.info", {"channel": channel_id})["channel"]
        roots = self._api(
            "conversations.history", {"channel": channel_id, "limit": min(limit, 200)}
        ).get("messages", [])
        messages: list[dict] = []
        for root in roots:
            if root.get("reply_count"):
                messages.extend(
                    self._api(
                        "conversations.replies",
                        {"channel": channel_id, "ts": root["ts"], "limit": 200},
                    ).get("messages", [])
                )
            else:
                messages.append(root)
        return info, messages

    def permalink(self, channel_id: str, ts: str) -> str:
        try:
            return self._api("chat.getPermalink", {"channel": channel_id, "message_ts": ts})[
                "permalink"
            ]
        except Exception:
            return f"slack://{channel_id}/{ts}"

    def _api(self, method: str, data: dict):
        token = self.token()
        if not token:
            raise ValueError("Slack is not connected")
        response = httpx.post(
            f"https://slack.com/api/{method}",
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise ValueError(f"Slack API error: {payload.get('error')}")
        return payload
