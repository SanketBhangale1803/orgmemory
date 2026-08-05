"""Workspace API-key authentication and isolation tests."""

import pytest
from fastapi import HTTPException

from app.api.routes import _authenticate, _authorize_project
from app.audit import AuditService
from app.auth.api_keys import create_api_key
from app.auth.app_auth import create_dev_session, create_workspace
from app.core.database import connect
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService


def _project_for_workspace(graph, workspace_id: str, name: str) -> str:
    project_id = IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(name)
    with connect() as conn:
        conn.execute("INSERT INTO workspace_projects VALUES (?,?)", (workspace_id, project_id))
    return project_id


def test_workspace_api_key_authenticates_and_isolates_projects(graph):
    owner = create_dev_session("cursor-owner@example.com", "Cursor Owner")
    workspace = create_workspace("Cursor Workspace", owner["token"])
    project_id = _project_for_workspace(graph, workspace["id"], "Cursor project")
    key = create_api_key("Cursor MCP", workspace["id"], created_by=owner["user"]["id"])

    principal = _authenticate(f"Bearer {key['api_key']}")

    assert principal["auth_type"] == "api_key"
    assert principal["active_workspace_id"] == workspace["id"]
    assert _authorize_project(project_id, f"Bearer {key['api_key']}")["api_key_id"] == key["id"]

    other_owner = create_dev_session("other-owner@example.com", "Other Owner")
    other_workspace = create_workspace("Other Workspace", other_owner["token"])
    other_project_id = _project_for_workspace(graph, other_workspace["id"], "Other project")

    with pytest.raises(HTTPException) as exc:
        _authorize_project(other_project_id, f"Bearer {key['api_key']}")
    assert exc.value.status_code == 403


def test_unscoped_legacy_key_is_rejected(graph):
    legacy_key = create_api_key("Legacy automation")

    with pytest.raises(HTTPException) as exc:
        _authenticate(f"Bearer {legacy_key['api_key']}")

    assert exc.value.status_code == 401
    assert "workspace-scoped" in str(exc.value.detail)
