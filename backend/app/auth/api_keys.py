"""Workspace API keys for MCP clients and automation.

Keys are shown once at creation and stored as SHA-256 hashes with a short
prefix for identification. Revocation is a tombstone, not a delete, so the
audit trail stays intact.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

from app.core.database import connect, new_id, row, rows, utcnow

KEY_PREFIX = "rbk"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def create_api_key(name: str, workspace_id: str = "", created_by: str = "") -> dict[str, Any]:
    if not name.strip():
        raise ValueError("API key name is required")
    secret = f"{KEY_PREFIX}_{secrets.token_urlsafe(32)}"
    key_id = new_id("key")
    now = utcnow()
    with connect() as conn:
        conn.execute(
            "INSERT INTO api_keys (id, workspace_id, name, key_prefix, key_hash, created_by, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (key_id, workspace_id, name.strip(), secret[:12], _hash(secret), created_by, now),
        )
    return {
        "id": key_id,
        "name": name.strip(),
        "workspace_id": workspace_id,
        "key_prefix": secret[:12],
        "created_at": now,
        # Returned exactly once; only the hash is stored.
        "api_key": secret,
    }


def list_api_keys(workspace_id: str = "") -> list[dict[str, Any]]:
    if workspace_id:
        records = rows(
            "SELECT id, workspace_id, name, key_prefix, created_by, created_at, last_used_at, revoked_at "
            "FROM api_keys WHERE workspace_id=? ORDER BY created_at DESC",
            (workspace_id,),
        )
    else:
        records = rows(
            "SELECT id, workspace_id, name, key_prefix, created_by, created_at, last_used_at, revoked_at "
            "FROM api_keys ORDER BY created_at DESC"
        )
    for record in records:
        record["status"] = "revoked" if record["revoked_at"] else "active"
    return records


def revoke_api_key(key_id: str) -> dict[str, Any]:
    record = row("SELECT id, revoked_at FROM api_keys WHERE id=?", (key_id,))
    if not record:
        raise ValueError("API key not found")
    if record["revoked_at"]:
        raise ValueError("API key is already revoked")
    now = utcnow()
    with connect() as conn:
        conn.execute("UPDATE api_keys SET revoked_at=? WHERE id=?", (now, key_id))
    return {"id": key_id, "status": "revoked", "revoked_at": now}


def verify_api_key(secret: str) -> dict[str, Any] | None:
    record = row(
        "SELECT id, workspace_id, name, revoked_at FROM api_keys WHERE key_hash=?",
        (_hash(secret),),
    )
    if not record or record["revoked_at"]:
        return None
    with connect() as conn:
        conn.execute("UPDATE api_keys SET last_used_at=? WHERE id=?", (utcnow(), record["id"]))
    return record
