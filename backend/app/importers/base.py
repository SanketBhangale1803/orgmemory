"""Migration layer from existing incident tools.

Importers move data from PagerDuty-class products into Runbook through the
same ingestion pipeline as every other source. An importer without
credentials reports `not_connected` and refuses to import — it never
pretends a migration happened.
"""

from __future__ import annotations

import os
from typing import Any


class NotConnectedError(RuntimeError):
    """Raised when an importer is used without credentials."""


class NotImplementedImporterError(RuntimeError):
    """Raised when a scaffolded importer method has no live client yet."""


class IncidentToolImporter:
    """Interface every incident-tool importer implements.

    Subclasses set `name`, `label`, and `token_env`. `implemented` marks
    whether a live API client exists; scaffolded importers expose the same
    interface but raise instead of faking results.
    """

    name: str = ""
    label: str = ""
    token_env: str = ""
    implemented: bool = False

    def token(self) -> str:
        return os.getenv(self.token_env, "")

    def connected(self) -> bool:
        return bool(self.token())

    def status(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "status": "connected" if self.connected() else "not_connected",
            "implemented": self.implemented,
            "token_env": self.token_env,
        }

    def _require_connection(self) -> None:
        if not self.connected():
            raise NotConnectedError(
                f"{self.label} is not connected. Set {self.token_env} to import."
            )
        if not self.implemented:
            raise NotImplementedImporterError(
                f"The {self.label} importer interface is scaffolded but its live API client "
                "is not implemented yet. No data was imported."
            )

    def list_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)

    def import_incidents(self, ingestion, project_id: str, limit: int = 50) -> dict[str, Any]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)

    def import_services(self, ingestion, project_id: str) -> dict[str, Any]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)

    def import_escalation_policies(self, ingestion, project_id: str) -> dict[str, Any]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)

    def import_postmortems(self, ingestion, project_id: str) -> dict[str, Any]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)

    def import_status_updates(self, ingestion, project_id: str) -> dict[str, Any]:
        self._require_connection()
        raise NotImplementedImporterError(self.label)
