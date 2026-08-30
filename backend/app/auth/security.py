from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe

from starlette.requests import Request

from app.core.config import settings
from app.core.database import connect, utcnow

from .vault import OAuthTokenVault


def _is_local_base(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


def public_base_url(request: Request) -> str:
    """The scheme://host the browser actually used to reach this deployment.

    Behind a proxy (Vercel rewrites, Compose fronting, cloud load balancers)
    the container sees an internal host, so the forwarded headers are the
    source of truth. An explicitly configured non-local ``PUBLIC_BASE_URL``
    always wins, which keeps signed redirects stable when a fixed domain is
    known.
    """
    configured = (settings.public_base_url or "").strip().rstrip("/")
    if configured and not _is_local_base(configured):
        return configured
    proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    proto = proto or request.url.scheme
    host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    host = host or request.headers.get("host", "")
    if host:
        return f"{proto}://{host}"
    return str(request.base_url).rstrip("/")


def oauth_redirect_uri(request: Request, configured: str, callback_path: str) -> str:
    """The redirect_uri for one OAuth round trip.

    A configured production URL is used verbatim. A configured or default
    localhost value is replaced by the host the request actually arrived on,
    so a deployment works without baking its domain into the environment —
    while staying byte-identical between the /start and /callback legs,
    because both legs run on the same public host.
    """
    candidate = (configured or "").strip()
    if candidate and not _is_local_base(candidate):
        return candidate
    return public_base_url(request) + callback_path


def frontend_redirect(request: Request, path: str) -> str:
    """Redirect the browser to the frontend surface it came from."""
    configured = (settings.frontend_url or "").strip().rstrip("/")
    base = configured if configured and not _is_local_base(configured) else public_base_url(request)
    return f"{base}{path}"


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
