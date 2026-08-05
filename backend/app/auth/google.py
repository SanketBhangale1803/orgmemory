from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.core.config import settings


def google_oauth_url(flow: dict[str, str]) -> str:
    if not (settings.google_client_id and settings.google_client_secret):
        raise ValueError("Google OAuth is not configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": flow["state"],
        "prompt": "select_account",
        "access_type": "online",
    }
    if flow.get("code_challenge"):
        params.update(
            {
                "code_challenge": flow["code_challenge"],
                "code_challenge_method": "S256",
            }
        )
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def complete_google_oauth(code: str, flow: dict) -> dict[str, str]:
    exchange = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.google_redirect_uri,
    }
    if flow.get("code_verifier"):
        exchange["code_verifier"] = flow["code_verifier"]
    response = httpx.post(
        "https://oauth2.googleapis.com/token",
        data=exchange,
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError("Google OAuth did not return an access token")
    profile_response = httpx.get(
        "https://openidconnect.googleapis.com/v1/userinfo",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    profile_response.raise_for_status()
    profile = profile_response.json()
    if not profile.get("sub") or not profile.get("email"):
        raise ValueError("Google did not return a usable identity")
    return {
        "external_id": str(profile["sub"]),
        "email": str(profile["email"]).casefold(),
        "display_name": str(profile.get("name") or profile["email"].split("@", 1)[0]),
        "avatar_url": str(profile.get("picture") or ""),
    }
