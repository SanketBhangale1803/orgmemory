"""Operational memory, importer honesty, and API key tests."""

import pytest

from app.audit import AuditService
from app.auth.api_keys import create_api_key, list_api_keys, revoke_api_key, verify_api_key
from app.hcag_adapter import HCAGAdapter
from app.importers import NotConnectedError, get_importer, importer_statuses
from app.ingestion import IngestionService
from app.memory import OperationalMemoryService


def test_operational_memory_requires_evidence_and_approval(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Memories")
    memories = OperationalMemoryService(graph)

    # Nothing ingested → nothing derived. No memory appears from thin air.
    assert memories.derive(project_id)["candidates_created"] == 0

    ingestion.ingest_item(
        project_id,
        "slack",
        "#cosmos-platform thread",
        "Production restarts of reddit_service require platform-team approval.\n"
        "Kafka incidents escalate to the platform team via #cosmos-platform.",
    )
    derived = memories.derive(project_id)
    assert derived["candidates_created"] >= 1
    candidate = derived["memories"][0]
    assert candidate["status"] == "proposed"
    assert candidate["evidence"], "every memory must cite its source line"
    assert candidate["source_item_ids"]

    approved = memories.resolve(candidate["id"], True, "test-admin")
    assert approved["status"] == "approved"
    assert approved["approved_by"] == "test-admin"
    # Approving twice is invalid.
    with pytest.raises(ValueError):
        memories.resolve(candidate["id"], True, "test-admin")
    # Re-deriving does not duplicate the same statement.
    assert memories.derive(project_id)["candidates_created"] == 0


def test_importers_fail_closed_without_credentials(graph, monkeypatch):
    for status in importer_statuses():
        monkeypatch.delenv(status["token_env"], raising=False)
    statuses = importer_statuses()
    assert {status["name"] for status in statuses} >= {
        "pagerduty",
        "rootly",
        "incident_io",
        "opsgenie",
        "statuspage",
        "jira_service_management",
        "servicenow",
    }
    assert all(status["status"] == "not_connected" for status in statuses)

    pagerduty = get_importer("pagerduty")
    with pytest.raises(NotConnectedError):
        pagerduty.import_incidents(None, "prj_x")
    # Scaffolded importers refuse to fake even when a token is present.
    monkeypatch.setenv("ROOTLY_API_TOKEN", "fake-token")
    rootly = get_importer("rootly")
    with pytest.raises(RuntimeError, match="not implemented"):
        rootly.import_incidents(None, "prj_x")


def test_api_key_lifecycle(graph):
    created = create_api_key("CI automation", workspace_id="ws_test")
    assert created["api_key"].startswith("rbk_")
    assert created["key_prefix"] == created["api_key"][:12]
    assert created["workspace_id"] == "ws_test"

    listed = list_api_keys("ws_test")
    assert listed and listed[0]["status"] == "active"
    assert "api_key" not in listed[0], "the secret must never be listed"
    assert "key_hash" not in listed[0]

    assert verify_api_key(created["api_key"])["id"] == created["id"]
    assert verify_api_key("rbk_wrong") is None

    revoke_api_key(created["id"])
    assert verify_api_key(created["api_key"]) is None
    assert list_api_keys("ws_test")[0]["status"] == "revoked"
    with pytest.raises(ValueError):
        revoke_api_key(created["id"])
