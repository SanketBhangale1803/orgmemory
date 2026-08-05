from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.auth import OAuthStateStore
from app.auth.google import google_oauth_url
from app.core.config import settings
from app.llm.providers import generate_grounded_json, model_catalog
from app.main import app


def test_local_loopback_origins_can_reach_the_api(graph):
    client = TestClient(app)

    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        response = client.options(
            "/api/auth/providers",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_email_code_login_issues_one_time_session(graph, monkeypatch):
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "email_auth_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "email_from", "")
    client = TestClient(app)

    requested = client.post("/api/auth/email/request", json={"email": "owner@example.com"})

    assert requested.status_code == 200
    payload = requested.json()
    assert payload["delivery"] == "development"
    assert len(payload["development_code"]) == 6

    verified = client.post(
        "/api/auth/email/verify",
        json={"email": "owner@example.com", "code": payload["development_code"]},
    )

    assert verified.status_code == 200
    assert verified.cookies.get(settings.session_cookie_name)
    assert verified.json()["user"]["auth_provider"] == "email"

    reused = client.post(
        "/api/auth/email/verify",
        json={"email": "owner@example.com", "code": payload["development_code"]},
    )
    assert reused.status_code == 400


def test_google_login_uses_pkce_and_redirects_to_workspace(graph, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "google-client")
    monkeypatch.setattr(settings, "google_client_secret", "google-secret")
    monkeypatch.setattr(
        settings,
        "google_redirect_uri",
        "http://localhost:8000/api/auth/google/callback",
    )
    flow = OAuthStateStore().create("google", intent="login", use_pkce=True)
    authorization = parse_qs(urlparse(google_oauth_url(flow)).query)

    assert authorization["client_id"] == ["google-client"]
    assert authorization["code_challenge_method"] == ["S256"]
    assert "openid" in authorization["scope"][0]

    monkeypatch.setattr(
        "app.api.routes.complete_google_oauth",
        lambda code, consumed_flow: {
            "external_id": "google-user-42",
            "email": "owner@example.com",
            "display_name": "Owner",
            "avatar_url": "",
        },
    )
    response = TestClient(app).get(
        "/api/auth/google/callback",
        params={"code": "oauth-code", "state": flow["state"]},
        follow_redirects=False,
    )

    assert response.status_code in {302, 307}
    assert response.headers["location"] == f"{settings.frontend_url.rstrip('/')}/workspace"
    assert response.cookies.get(settings.session_cookie_name)


def test_provider_and_model_catalogs_expose_readiness_without_secrets(graph, monkeypatch):
    monkeypatch.setattr(settings, "github_client_id", "")
    monkeypatch.setattr(settings, "github_client_secret", "")
    monkeypatch.setattr(settings, "openai_api_key", "configured-but-secret")
    response = TestClient(app).get("/api/auth/providers")
    models_response = TestClient(app).get("/api/models")

    assert response.status_code == 200
    assert response.json()["github"] is False
    assert "GITHUB_CLIENT_ID" in response.json()["details"]["github"]["setup"]
    assert models_response.status_code == 200
    assert next(item for item in model_catalog() if item["id"] == "gpt")["configured"] is True
    assert "configured-but-secret" not in models_response.text


def test_openai_compatible_and_gemini_requests_use_current_provider_contracts(graph, monkeypatch):
    calls: list[dict] = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def post(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if "generativelanguage" in url:
            return Response(
                {"candidates": [{"content": {"parts": [{"text": '{"answer":"gemini"}'}]}}]}
            )
        return Response({"choices": [{"message": {"content": '{"answer":"compatible"}'}}]})

    monkeypatch.setattr("app.llm.providers.httpx.post", post)
    monkeypatch.setattr(settings, "kimi_api_key", "kimi-secret")
    monkeypatch.setattr(settings, "google_api_key", "google-secret")

    kimi = generate_grounded_json("prompt", "kimi")
    gemini = generate_grounded_json("prompt", "gemini")

    assert kimi and kimi[0]["answer"] == "compatible"
    assert calls[0]["url"] == "https://api.moonshot.ai/v1/chat/completions"
    assert "temperature" not in calls[0]["json"]
    assert calls[0]["json"]["thinking"] == {"type": "disabled"}
    assert gemini and gemini[0]["answer"] == "gemini"
    assert calls[1]["headers"]["x-goog-api-key"] == "google-secret"
    assert "params" not in calls[1]
    assert "temperature" not in calls[1]["json"]["generationConfig"]
