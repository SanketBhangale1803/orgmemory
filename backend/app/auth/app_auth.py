from __future__ import annotations

import hashlib
import hmac
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from secrets import randbelow
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


def _pending_invite_workspace(user_id: str) -> str | None:
    """Claim the most recent outstanding invitation for a user, if one exists.

    An invitation is declared intent to join. Landing an invited person in their
    own private workspace instead would strand them outside the team they were
    added to, so sign-in activates the membership.
    """
    invitation = row(
        """SELECT m.id, m.workspace_id FROM workspace_members m
        WHERE m.user_id=? AND m.status='invited'
        ORDER BY m.created_at DESC LIMIT 1""",
        (user_id,),
    )
    if not invitation:
        return None
    with connect() as conn:
        conn.execute(
            "UPDATE workspace_members SET status='active',updated_at=? WHERE id=?",
            (utcnow(), invitation["id"]),
        )
    return invitation["workspace_id"]


def create_dev_session(
    email: str = "demo@runbook.local", display_name: str = "Demo User"
) -> dict[str, Any]:
    if not settings.auth_dev_mode:
        raise ValueError("Dev login is disabled")
    now = utcnow()
    user = row("SELECT * FROM users WHERE email=?", (email,))
    user_id = user["id"] if user else new_id("usr")
    with connect() as conn:
        if user:
            # A local session must not replace a GitHub identity: SQLite
            # REPLACE deletes the user row and cascades workspace membership.
            conn.execute(
                "UPDATE users SET display_name=?,updated_at=? WHERE id=?",
                (display_name, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                (user_id, email, display_name, "dev", email, "owner", now, now),
            )
    membership = row(
        """SELECT m.workspace_id FROM workspace_members m
        JOIN workspaces w ON w.id=m.workspace_id
        WHERE m.user_id=? AND m.status='active'
        ORDER BY CASE WHEN w.slug=? THEN 1 ELSE 0 END,m.created_at LIMIT 1""",
        (user_id, DEFAULT_WORKSPACE_SLUG),
    )
    workspace_id = (
        membership["workspace_id"] if membership else _pending_invite_workspace(user_id)
    ) or ensure_workspace("Local workspace", DEFAULT_WORKSPACE_SLUG, user_id, "owner")["id"]
    return issue_session(user_id, workspace_id)


def create_oauth_session(
    provider: str,
    external_id: str,
    email: str,
    display_name: str,
    workspace_name: str,
) -> dict[str, Any]:
    """Create or refresh a real identity and issue a workspace-bound session."""
    now = utcnow()
    user = row(
        "SELECT * FROM users WHERE auth_provider=? AND external_id=?",
        (provider, external_id),
    ) or row("SELECT * FROM users WHERE email=?", (email,))
    user_id = user["id"] if user else new_id("usr")
    with connect() as conn:
        if user:
            conn.execute(
                "UPDATE users SET email=?,display_name=?,auth_provider=?,external_id=?,updated_at=? WHERE id=?",
                (email, display_name, provider, external_id, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO users VALUES (?,?,?,?,?,?,?,?)",
                (user_id, email, display_name, provider, external_id, "owner", now, now),
            )
    membership = row(
        "SELECT workspace_id FROM workspace_members WHERE user_id=? AND status='active' ORDER BY created_at LIMIT 1",
        (user_id,),
    )
    workspace_id = membership["workspace_id"] if membership else None
    if not workspace_id:
        # No active home yet, so an outstanding invitation takes priority over
        # spinning up a fresh personal workspace.
        workspace_id = _pending_invite_workspace(user_id)
    if not workspace_id:
        base_slug = slugify(workspace_name)
        slug = base_slug
        suffix = 2
        while row("SELECT id FROM workspaces WHERE slug=?", (slug,)):
            slug = f"{base_slug[:54]}-{suffix}"
            suffix += 1
        workspace_id = ensure_workspace(workspace_name, slug, user_id, "owner")["id"]
    return issue_session(user_id, workspace_id)


def request_email_login_code(email: str) -> dict[str, Any]:
    """Issue a short-lived, one-time sign-in code without storing the raw code."""
    normalized = email.strip().casefold()
    if not settings.email_auth_enabled:
        raise ValueError("Email sign-in is disabled")
    if not settings.auth_dev_mode and not (settings.smtp_host and settings.email_from):
        raise ValueError("Email delivery is not configured")

    now = datetime.now(UTC)
    latest = row(
        "SELECT created_at FROM email_login_codes WHERE email=? ORDER BY created_at DESC LIMIT 1",
        (normalized,),
    )
    if (
        latest
        and (now - datetime.fromisoformat(latest["created_at"])).total_seconds()
        < settings.email_code_resend_seconds
    ):
        raise ValueError("Please wait before requesting another sign-in code")
    code = f"{randbelow(1_000_000):06d}"
    expires_at = (now + timedelta(minutes=settings.email_code_ttl_minutes)).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE email_login_codes SET used_at=? WHERE email=? AND used_at IS NULL",
            (now.isoformat(), normalized),
        )
        conn.execute(
            """INSERT INTO email_login_codes
            (id,email,code_hash,attempts,expires_at,used_at,created_at)
            VALUES (?,?,?,?,?,NULL,?)""",
            (
                new_id("emc"),
                normalized,
                _hash_email_code(normalized, code),
                0,
                expires_at,
                now.isoformat(),
            ),
        )

    if settings.smtp_host and settings.email_from:
        _send_login_code(normalized, code)
        return {
            "sent": True,
            "delivery": "email",
            "expires_in_seconds": settings.email_code_ttl_minutes * 60,
        }
    return {
        "sent": True,
        "delivery": "development",
        "development_code": code,
        "expires_in_seconds": settings.email_code_ttl_minutes * 60,
    }


def verify_email_login_code(email: str, code: str) -> dict[str, Any]:
    normalized = email.strip().casefold()
    record = row(
        """SELECT * FROM email_login_codes
        WHERE email=? AND used_at IS NULL ORDER BY created_at DESC LIMIT 1""",
        (normalized,),
    )
    if not record:
        raise ValueError("The sign-in code is invalid or expired")
    now = datetime.now(UTC)
    if datetime.fromisoformat(record["expires_at"]) < now or int(record["attempts"]) >= 5:
        with connect() as conn:
            conn.execute(
                "UPDATE email_login_codes SET used_at=? WHERE id=?",
                (now.isoformat(), record["id"]),
            )
        raise ValueError("The sign-in code is invalid or expired")
    if not hmac.compare_digest(
        record["code_hash"],
        _hash_email_code(normalized, code),
    ):
        with connect() as conn:
            conn.execute(
                "UPDATE email_login_codes SET attempts=attempts+1 WHERE id=?",
                (record["id"],),
            )
        raise ValueError("The sign-in code is invalid or expired")

    with connect() as conn:
        conn.execute(
            "UPDATE email_login_codes SET used_at=? WHERE id=?",
            (now.isoformat(), record["id"]),
        )
    local_part, _, domain = normalized.partition("@")
    display_name = local_part.replace(".", " ").replace("_", " ").title() or normalized
    workspace_name = f"{domain or 'Company'} workspace"
    return create_oauth_session(
        "email",
        normalized,
        normalized,
        display_name,
        workspace_name,
    )


def issue_session(user_id: str, workspace_id: str | None = None) -> dict[str, Any]:
    token = _token()
    now = utcnow()
    expires = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    with connect() as conn:
        conn.execute(
            """INSERT INTO sessions
            (id,user_id,workspace_id,token_hash,expires_at,created_at)
            VALUES (?,?,?,?,?,?)""",
            (new_id("ses"), user_id, workspace_id or "", _hash_token(token), expires, now),
        )
    return {"token": token, "expires_at": expires, "user": me_for_user(user_id, workspace_id)}


def ensure_workspace(name: str, slug: str, owner_id: str, role: str = "owner") -> dict[str, Any]:
    now = utcnow()
    workspace = row("SELECT * FROM workspaces WHERE slug=?", (slug,))
    workspace_id = workspace["id"] if workspace else new_id("wsp")
    membership = row(
        "SELECT id,created_at FROM workspace_members WHERE workspace_id=? AND user_id=?",
        (workspace_id, owner_id),
    )
    with connect() as conn:
        conn.execute(
            """INSERT INTO workspaces(id,name,slug,created_at,updated_at) VALUES (?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name,slug=excluded.slug,
            updated_at=excluded.updated_at""",
            (workspace_id, name, slug, workspace["created_at"] if workspace else now, now),
        )
        conn.execute(
            """INSERT INTO workspace_members
            (id,workspace_id,user_id,role,status,invited_email,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(workspace_id,user_id) DO UPDATE SET role=excluded.role,
            status=excluded.status,updated_at=excluded.updated_at""",
            (
                membership["id"] if membership else new_id("mem"),
                workspace_id,
                owner_id,
                role,
                "active",
                "",
                membership["created_at"] if membership else now,
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
    return me_for_user(session["user_id"], session.get("workspace_id") or None)


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


def _hash_email_code(email: str, code: str) -> str:
    payload = f"{email}:{code}".encode()
    return hmac.new(settings.jwt_secret.encode(), payload, hashlib.sha256).hexdigest()


def _send_login_code(email: str, code: str) -> None:
    message = EmailMessage()
    message["Subject"] = f"{code} is your OrgMemory sign-in code"
    message["From"] = settings.email_from
    message["To"] = email
    message.set_content(
        "Use this one-time code to sign in to OrgMemory:\n\n"
        f"{code}\n\n"
        f"It expires in {settings.email_code_ttl_minutes} minutes. "
        "If you did not request it, you can ignore this email."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def slugify(value: str) -> str:
    slug = "-".join(
        part for part in "".join(c.lower() if c.isalnum() else " " for c in value).split() if part
    )
    return slug[:60] or "workspace"
