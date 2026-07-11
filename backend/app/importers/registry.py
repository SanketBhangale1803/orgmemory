"""Importer registry. PagerDuty has a live REST client; the rest expose the
same interface and honestly report that their live client is not implemented.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import IncidentToolImporter


class PagerDutyImporter(IncidentToolImporter):
    name = "pagerduty"
    label = "PagerDuty"
    token_env = "PAGERDUTY_API_TOKEN"
    implemented = True
    api = "https://api.pagerduty.com"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = httpx.get(
            f"{self.api}{path}",
            params=params or {},
            headers={
                "Authorization": f"Token token={self.token()}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        self._require_connection()
        return self._get("/incidents", {"limit": min(limit, 100), "sort_by": "created_at:desc"})[
            "incidents"
        ]

    def import_incidents(self, ingestion, project_id: str, limit: int = 50) -> dict[str, Any]:
        incidents = self.list_incidents(limit)
        imported = 0
        for incident in incidents:
            title = (
                f"PagerDuty incident {incident.get('incident_number')}: {incident.get('title', '')}"
            )
            content = "\n".join(
                f"{key}: {incident.get(key)}"
                for key in ("status", "urgency", "created_at", "resolved_at", "summary")
                if incident.get(key)
            )
            service = (incident.get("service") or {}).get("summary", "")
            if service:
                content += f"\nservice: {service}"
            ingestion.ingest_item(
                project_id,
                "incident",
                title,
                content,
                incident.get("html_url", ""),
                metadata={"importer": self.name, "external_id": incident.get("id")},
            )
            imported += 1
        return {"importer": self.name, "incidents_imported": imported}

    def import_services(self, ingestion, project_id: str) -> dict[str, Any]:
        self._require_connection()
        services = self._get("/services", {"limit": 100})["services"]
        imported = 0
        for service in services:
            ingestion.ingest_item(
                project_id,
                "doc",
                f"PagerDuty service: {service.get('name', '')}",
                f"name: {service.get('name')}\ndescription: {service.get('description') or ''}\n"
                f"status: {service.get('status')}",
                service.get("html_url", ""),
                metadata={"importer": self.name, "external_id": service.get("id")},
            )
            imported += 1
        return {"importer": self.name, "services_imported": imported}


class RootlyImporter(IncidentToolImporter):
    name = "rootly"
    label = "Rootly"
    token_env = "ROOTLY_API_TOKEN"


class IncidentIOImporter(IncidentToolImporter):
    name = "incident_io"
    label = "incident.io"
    token_env = "INCIDENT_IO_API_TOKEN"


class OpsgenieImporter(IncidentToolImporter):
    name = "opsgenie"
    label = "Opsgenie"
    token_env = "OPSGENIE_API_TOKEN"


class StatuspageImporter(IncidentToolImporter):
    name = "statuspage"
    label = "Statuspage"
    token_env = "STATUSPAGE_API_TOKEN"


class JiraServiceManagementImporter(IncidentToolImporter):
    name = "jira_service_management"
    label = "Jira Service Management"
    token_env = "JSM_API_TOKEN"


class ServiceNowImporter(IncidentToolImporter):
    name = "servicenow"
    label = "ServiceNow"
    token_env = "SERVICENOW_API_TOKEN"


IMPORTERS: dict[str, IncidentToolImporter] = {
    importer.name: importer
    for importer in (
        PagerDutyImporter(),
        RootlyImporter(),
        IncidentIOImporter(),
        OpsgenieImporter(),
        StatuspageImporter(),
        JiraServiceManagementImporter(),
        ServiceNowImporter(),
    )
}


def get_importer(name: str) -> IncidentToolImporter:
    importer = IMPORTERS.get(name)
    if not importer:
        raise ValueError(f"Unknown importer: {name}")
    return importer


def importer_statuses() -> list[dict[str, Any]]:
    return [importer.status() for importer in IMPORTERS.values()]
