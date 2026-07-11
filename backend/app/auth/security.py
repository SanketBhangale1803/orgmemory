from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.database import connect, new_id, rows, utcnow


class ConnectorSecrets:
    def __init__(self):
        key_path = settings.sqlite_path.parent / ".connector_key"
        if settings.integration_encryption_key:
            key = settings.integration_encryption_key.encode()
        elif key_path.exists():
            key = key_path.read_bytes().strip()
        else:
            key_path.parent.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            key_path.write_bytes(key)
            key_path.chmod(0o600)
        self.cipher = Fernet(key)

    def save(
        self,
        provider: str,
        external_id: str,
        display_name: str,
        token: str,
        metadata: dict | None = None,
    ) -> str:
        connection_id, now = new_id("conn"), utcnow()
        encrypted = self.cipher.encrypt(token.encode()).decode()
        with connect() as conn:
            conn.execute(
                """INSERT INTO connector_accounts VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(provider,external_id) DO UPDATE SET display_name=excluded.display_name,status='connected',secret_encrypted=excluded.secret_encrypted,metadata_json=excluded.metadata_json,updated_at=excluded.updated_at""",
                (
                    connection_id,
                    provider,
                    external_id,
                    display_name,
                    "connected",
                    encrypted,
                    json.dumps(metadata or {}),
                    now,
                    now,
                ),
            )
        return connection_id

    def token(self, provider: str) -> str | None:
        accounts = rows(
            "SELECT secret_encrypted FROM connector_accounts WHERE provider=? AND status='connected' ORDER BY updated_at DESC LIMIT 1",
            (provider,),
        )
        return (
            self.cipher.decrypt(accounts[0]["secret_encrypted"].encode()).decode()
            if accounts
            else None
        )

    def status(self, provider: str) -> list[dict]:
        return rows(
            "SELECT id,external_id,display_name,status,metadata_json,created_at,updated_at FROM connector_accounts WHERE provider=? ORDER BY updated_at DESC",
            (provider,),
        )


class OAuthStateStore:
    def create(self, provider: str) -> str:
        state = token_urlsafe(32)
        expires = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
        with connect() as conn:
            conn.execute("INSERT INTO oauth_states VALUES (?,?,?,NULL)", (state, provider, expires))
        return state

    def consume(self, provider: str, state: str) -> None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM oauth_states WHERE state=? AND provider=?", (state, provider)
            ).fetchone()
            if (
                not row
                or row["used_at"]
                or datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC)
            ):
                raise ValueError("OAuth state is invalid or expired")
            conn.execute("UPDATE oauth_states SET used_at=? WHERE state=?", (utcnow(), state))
