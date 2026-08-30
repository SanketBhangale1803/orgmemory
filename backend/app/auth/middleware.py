from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.api_keys import verify_api_key
from app.auth.app_auth import bearer_token, me_from_token
from app.auth.mcp_oauth import principal_from_mcp_token
from app.core.config import settings

PUBLIC_API_PATHS = {
    "/api/health",
    "/api/health/graph",
    "/api/auth/providers",
    "/api/auth/demo-login",
    "/api/models",
    "/api/platforms",
    "/api/auth/dev-login",
    "/api/auth/email/request",
    "/api/auth/email/verify",
    "/api/auth/github/start",
    "/api/auth/github/callback",
    "/api/auth/google/start",
    "/api/auth/google/callback",
    "/api/connectors/github/auth/callback",
    "/api/connectors/slack/auth/callback",
    "/api/auth/slack/callback",
    "/api/webhooks/github",
}

PUBLIC_DEMO_BLOCKED_MUTATION_PREFIXES = (
    "/api/connectors",
    "/api/execute",
    "/api/importers",
    "/api/ingest",
    "/api/keys",
    "/api/mcp/oauth/clients",
)


class AuthenticationBoundaryMiddleware(BaseHTTPMiddleware):
    """Make authentication the default boundary for every application API."""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/") or "/"
        if (
            not path.startswith("/api")
            or path in PUBLIC_API_PATHS
            or path.startswith("/api/webhooks/")
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        authorization = request.headers.get("authorization", "")
        if not authorization:
            cookie_token = request.cookies.get(settings.session_cookie_name, "")
            if cookie_token:
                headers = list(request.scope["headers"])
                headers.append((b"authorization", f"Bearer {cookie_token}".encode()))
                request.scope["headers"] = headers
                authorization = f"Bearer {cookie_token}"

        token = bearer_token(authorization)
        if not token or (
            not me_from_token(token)
            and not verify_api_key(token)
            and not principal_from_mcp_token(token)
        ):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        if (
            settings.public_demo_mode
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and path.startswith(PUBLIC_DEMO_BLOCKED_MUTATION_PREFIXES)
        ):
            return JSONResponse(
                {
                    "detail": (
                        "This external integration or execution path is disabled "
                        "in the public demo"
                    )
                },
                status_code=403,
            )
        return await call_next(request)
