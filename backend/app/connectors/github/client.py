from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from app.auth import ConnectorSecrets, OAuthStateStore
from app.connectors.base import Connector, ConnectorStatus
from app.core.config import settings


class GitHubConnector(Connector):
    def __init__(self, secrets: ConnectorSecrets | None = None):
        self.secrets = secrets or ConnectorSecrets()

    def token(self) -> str | None:
        return settings.github_token or self.secrets.token("github")

    def status(self) -> ConnectorStatus:
        accounts = self.secrets.status("github")
        return ConnectorStatus("github", True, bool(self.token()), accounts)

    def oauth_url(self, state_store: OAuthStateStore) -> str:
        if not settings.github_client_id:
            raise ValueError("GitHub OAuth is not configured")
        state = state_store.create("github")
        return "https://github.com/login/oauth/authorize?" + urlencode(
            {
                "client_id": settings.github_client_id,
                "redirect_uri": settings.github_redirect_uri,
                "scope": "repo read:org",
                "state": state,
            }
        )

    def complete_oauth(self, code: str, state: str, state_store: OAuthStateStore) -> dict:
        state_store.consume("github", state)
        response = httpx.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise ValueError("GitHub OAuth did not return an access token")
        user = self._api("GET", "/user", token=token)
        self.secrets.save("github", str(user["id"]), user["login"], token)
        return {"login": user["login"]}

    def list_repositories(self) -> list[dict[str, Any]]:
        return self._api("GET", "/user/repos?per_page=100&sort=updated")

    def list_issues(self, slug: str) -> list[dict[str, Any]]:
        return [
            item
            for item in self._api("GET", f"/repos/{slug}/issues?state=all&per_page=100")
            if "pull_request" not in item
        ]

    def list_pull_requests(self, slug: str) -> list[dict[str, Any]]:
        return self._api("GET", f"/repos/{slug}/pulls?state=all&per_page=50")

    def pull_request_files(self, slug: str, number: int) -> list[dict[str, Any]]:
        return self._api("GET", f"/repos/{slug}/pulls/{number}/files?per_page=100")

    def clone(self, source: str, target: Path) -> None:
        token = self.token()
        env = None
        askpass = None
        if token:
            askpass = target.parent / ".runbook-askpass.sh"
            askpass.write_text(
                '#!/bin/sh\ncase "$1" in *Username*) echo x-access-token;; *) echo "$RUNBOOK_GITHUB_TOKEN";; esac\n'
            )
            askpass.chmod(0o700)
            env = {
                **os.environ,
                "GIT_ASKPASS": str(askpass),
                "GIT_TERMINAL_PROMPT": "0",
                "RUNBOOK_GITHUB_TOKEN": token,
            }
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", source, str(target)],
                capture_output=True,
                text=True,
                timeout=180,
                env=env,
            )
        finally:
            if askpass:
                askpass.unlink(missing_ok=True)
        if result.returncode:
            raise ValueError(f"Repository clone failed: {result.stderr.strip()[-400:]}")

    @staticmethod
    def slug(source: str) -> str | None:
        if "github.com" not in source:
            return None
        return urlparse(source).path.strip("/").removesuffix(".git")

    def _api(self, method: str, path: str, token: str | None = None):
        token = token or self.token()
        if not token:
            raise ValueError("GitHub is not connected")
        response = httpx.request(
            method,
            f"https://api.github.com{path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
