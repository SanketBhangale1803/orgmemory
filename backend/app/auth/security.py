from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from app.core.database import connect, utcnow

from .vault import OAuthTokenVault


class ConnectorSecrets(OAuthTokenVault):
    """Backward-compatible name for the production OAuth token vault."""


class OAuthStateStore:
    def create(
        self,
        provider: str,
        *,
        intent: str = "connect",
        workspace_id: str = "",
        user_id: str = "",
        use_pkce: bool = False,
    ) -> dict[str, str]:
        state = token_urlsafe(32)
        verifier = token_urlsafe(64) if use_pkce else ""
        expires = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
        with connect() as conn:
            conn.execute(
                "INSERT INTO oauth_flows VALUES (?,?,?,?,?,?,?,NULL)",
                (state, provider, intent, workspace_id, user_id, verifier, expires),
            )
        challenge = ""
        if verifier:
            digest = hashlib.sha256(verifier.encode()).digest()
            challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        return {"state": state, "code_challenge": challenge}

    def consume(self, provider: str, state: str) -> dict:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM oauth_flows WHERE state=? AND provider=?",
                (state, provider),
            ).fetchone()
            if (
                not row
                or row["used_at"]
                or datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC)
            ):
                raise ValueError("OAuth state is invalid or expired")
            conn.execute("UPDATE oauth_flows SET used_at=? WHERE state=?", (utcnow(), state))
            return dict(row)
