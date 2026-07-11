from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.core.database import connect, new_id, row, rows, utcnow

DEFAULT_WORKSPACE_SLUG = "local"


@dataclass
class Principal:
    user_id: str
    email: str
    display_name: str
    workspace_id: str
    role: str


def create_dev_session(
    email: str = "demo@runbook.local", display_name: str = "Demo User"
) -> dict[str, Any]:
    if not settings.auth_dev_mode:
        raise ValueError("Dev login is disabled")
    now = utcnow()
    user = row("SELECT * FROM users WHERE email=?", (email,))
    user_id = user["id"] if user else new_id("usr")
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?)",
            (
                user_id,
                email,
                display_name,
                "dev",
                email,
                "owner",
                user["created_at"] if user else now,
                now,
            ),
        )
    workspace = ensure_workspace("Local workspace", DEFAULT_WORKSPACE_SLUG, user_id, "owner")
    token = _token()
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?,?,?,?,?)",
            (new_id("ses"), user_id, _hash_token(token), expires, now),
        )
    return {"token": token, "expires_at": expires, "user": me_for_user(user_id, workspace["id"])}


def ensure_workspace(name: str, slug: str, owner_id: str, role: str = "owner") -> dict[str, Any]:
    now = utcnow()
    workspace = row("SELECT * FROM workspaces WHERE slug=?", (slug,))
    workspace_id = workspace["id"] if workspace else new_id("wsp")
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO workspaces VALUES (?,?,?,?,?)",
            (workspace_id, name, slug, workspace["created_at"] if workspace else now, now),
        )
        conn.execute(
            "INSERT OR REPLACE INTO workspace_members VALUES (?,?,?,?,?,?,?,?)",
            (
                (
                    row(
                        "SELECT id FROM workspace_members WHERE workspace_id=? AND user_id=?",
                        (workspace_id, owner_id),
                    )["id"]
                    if row(
                        "SELECT id FROM workspace_members WHERE workspace_id=? AND user_id=?",
                        (workspace_id, owner_id),
                    )
                    else new_id("mem")
                ),
                workspace_id,
                owner_id,
                role,
                "active",
                "",
                now,
                now,
            ),
        )
    return {"id": workspace_id, "name": name, "slug": slug}


def me_from_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    session = row("SELECT * FROM sessions WHERE token_hash=?", (_hash_token(token),))
    if not session:
        return None
    if session["expires_at"] < datetime.now(UTC).isoformat():
        return None
    return me_for_user(session["user_id"])


def me_for_user(user_id: str, workspace_id: str | None = None) -> dict[str, Any]:
    user = row("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        raise ValueError("User not found")
    memberships = rows(
        """
        SELECT wm.*, w.name workspace_name, w.slug workspace_slug
        FROM workspace_members wm
        JOIN workspaces w ON w.id=wm.workspace_id
        WHERE wm.user_id=? AND wm.status='active'
        ORDER BY wm.created_at ASC
        """,
        (user_id,),
    )
    active = next((item for item in memberships if item["workspace_id"] == workspace_id), None)
    active = active or (memberships[0] if memberships else None)
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "auth_provider": user["auth_provider"],
        "active_workspace_id": active["workspace_id"] if active else "",
        "role": active["role"] if active else "viewer",
        "workspaces": [
            {
                "id": item["workspace_id"],
                "name": item["workspace_name"],
                "slug": item["workspace_slug"],
                "role": item["role"],
            }
            for item in memberships
        ],
    }


def create_workspace(name: str, owner_token: str | None = None) -> dict[str, Any]:
    principal = me_from_token(owner_token)
    if not principal:
        dev = create_dev_session()
        principal = dev["user"]
    slug = slugify(name)
    return ensure_workspace(name, slug, principal["id"], "owner")


def list_workspaces(token: str | None = None) -> list[dict[str, Any]]:
    principal = me_from_token(token)
    if principal:
        return principal["workspaces"]
    if settings.auth_dev_mode:
        return create_dev_session()["user"]["workspaces"]
    return []


def workspace_members(workspace_id: str) -> list[dict[str, Any]]:
    return rows(
        """
        SELECT wm.id, wm.workspace_id, wm.role, wm.status, wm.invited_email,
               u.id user_id, u.email, u.display_name
        FROM workspace_members wm
        JOIN users u ON u.id=wm.user_id
        WHERE wm.workspace_id=?
        ORDER BY wm.created_at ASC
        """,
        (workspace_id,),
    )


def invite_member(workspace_id: str, email: str, role: str = "member") -> dict[str, Any]:
    if role not in {"owner", "admin", "member", "viewer"}:
        raise ValueError("Unsupported role")
    now = utcnow()
    user = row("SELECT * FROM users WHERE email=?", (email,))
    user_id = user["id"] if user else new_id("usr")
    with connect() as conn:
        if not user:
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                (user_id, email, email.split("@")[0], "invite", email, role, now, now),
            )
        conn.execute(
            "INSERT OR REPLACE INTO workspace_members VALUES (?,?,?,?,?,?,?,?)",
            (new_id("mem"), workspace_id, user_id, role, "invited", email, now, now),
        )
    return {"workspace_id": workspace_id, "email": email, "role": role, "status": "invited"}


def logout(token: str | None) -> dict[str, bool]:
    if token:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash=?", (_hash_token(token),))
    return {"logged_out": True}


def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    return authorization[len(prefix) :] if authorization.startswith(prefix) else authorization


def _token() -> str:
    return "rb_" + uuid4().hex + uuid4().hex


def _hash_token(token: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), token.encode(), hashlib.sha256).hexdigest()


def slugify(value: str) -> str:
    slug = "-".join(
        part for part in "".join(c.lower() if c.isalnum() else " " for c in value).split() if part
    )
    return slug[:60] or "workspace"
