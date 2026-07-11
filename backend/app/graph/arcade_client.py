from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings, settings


class ArcadeDBError(RuntimeError):
    pass


class ArcadeClient:
    def __init__(self, config: Settings = settings):
        self.config = config
        self.auth = (config.arcadedb_user, config.arcadedb_password)

    def health(self) -> dict[str, Any]:
        try:
            ready = httpx.get(f"{self.config.arcadedb_url}/api/v1/ready", timeout=3)
            exists = httpx.get(
                f"{self.config.arcadedb_url}/api/v1/exists/{self.config.arcadedb_database}",
                auth=self.auth,
                timeout=3,
            )
            return {
                "backend": "arcadedb",
                "connected": ready.status_code == 204 and exists.status_code == 200,
                "database": self.config.arcadedb_database,
            }
        except httpx.HTTPError:
            return {
                "backend": "arcadedb",
                "connected": False,
                "database": self.config.arcadedb_database,
            }

    def ensure_database(self) -> None:
        response = httpx.get(
            f"{self.config.arcadedb_url}/api/v1/exists/{self.config.arcadedb_database}",
            auth=self.auth,
            timeout=10,
        )
        if response.status_code == 200 and response.json().get("result") is True:
            return
        self._request(
            "/api/v1/server", {"command": f"create database {self.config.arcadedb_database}"}
        )

    def command(
        self, command: str, params: dict[str, Any] | None = None, language: str = "sql"
    ) -> list[dict[str, Any]]:
        payload = {
            "language": language,
            "command": command,
            "params": params or {},
            "autoCommit": True,
        }
        return self._request(f"/api/v1/command/{self.config.arcadedb_database}", payload).get(
            "result", []
        )

    def query(
        self, command: str, params: dict[str, Any] | None = None, language: str = "sql"
    ) -> list[dict[str, Any]]:
        payload = {"language": language, "command": command, "params": params or {}}
        return self._request(f"/api/v1/query/{self.config.arcadedb_database}", payload).get(
            "result", []
        )

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.config.arcadedb_url}{path}", json=payload, auth=self.auth, timeout=30
        )
        if response.status_code >= 400:
            raise ArcadeDBError(f"ArcadeDB {response.status_code}: {response.text[:500]}")
        return response.json()
