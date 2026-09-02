"""Scale hardening: sync-job lease reclaim, API guard (body cap + rate limits)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.connectors.sync import JOB_LEASE_MINUTES, SyncEngine
from app.core.config import settings
from app.core.database import connect, decode, row, utcnow
from app.main import app


def _insert_job(job_id: str, workspace_id: str, user_id: str, status: str, updated_at: str) -> None:
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """INSERT INTO connector_sync_jobs
            (id,workspace_id,user_id,provider,resource_id,project_id,cursor_json,
             status,attempts,max_attempts,next_attempt_at,last_error,idempotency_key,
             created_at,updated_at,completed_at)
            VALUES (?,?,?,?,?,?,?,?,0,?,?, '',?,?,?,NULL)""",
            (
                job_id,
                workspace_id,
                user_id,
                "github",
                "resource-1",
                "",
                "{}",
                status,
                5,
                now,
                f"key-{job_id}",
                now,
                updated_at,
            ),
        )


def _workspace_context() -> tuple[str, str]:
    from app.auth.app_auth import create_dev_session, create_workspace

    user = create_dev_session("scale-worker@example.com", "Scale Worker")
    workspace = create_workspace("Scale Workspace", f"Bearer {user['token']}")
    return workspace["id"], user["user"]["id"]


def test_run_once_reclaims_stale_running_jobs(graph):
    workspace_id, user_id = _workspace_context()
    engine = SyncEngine(apply_record=lambda record, context: None)
    stale_timestamp = (datetime.now(UTC) - timedelta(minutes=JOB_LEASE_MINUTES + 5)).isoformat()
    _insert_job("sync_stale_1", workspace_id, user_id, "running", stale_timestamp)
    _insert_job("sync_fresh_1", workspace_id, user_id, "running", utcnow())

    engine.run_once(limit=10)
    stale = row("SELECT status FROM connector_sync_jobs WHERE id='sync_stale_1'")
    fresh = row("SELECT status FROM connector_sync_jobs WHERE id='sync_fresh_1'")
    # The stale lease goes back through the queue (and, with no grant, onto the
    # retry path); the fresh lease is untouched.
    assert stale["status"] in {"queued", "retrying", "failed"}
    assert fresh["status"] == "running"


def test_reclaimed_job_is_reprocessable(graph):
    workspace_id, user_id = _workspace_context()
    engine = SyncEngine(apply_record=lambda record, context: None)
    stale_timestamp = (datetime.now(UTC) - timedelta(minutes=JOB_LEASE_MINUTES * 3)).isoformat()
    _insert_job("sync_stale_2", workspace_id, user_id, "running", stale_timestamp)
    engine.run_once(limit=10)
    job = decode(row("SELECT * FROM connector_sync_jobs WHERE id='sync_stale_2'"))
    assert job["status"] in {"retrying", "failed"}
    assert job["attempts"] >= 1


def test_api_guard_rejects_oversized_bodies(graph):
    limit_before = settings.api_max_body_bytes
    settings.api_max_body_bytes = 64
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/auth/dev-login",
                json={"email": "guard@example.com", "display_name": "Guard", "pad": "x" * 4096},
            )
            assert response.status_code == 413
    finally:
        settings.api_max_body_bytes = limit_before


def test_api_guard_rate_limits_public_paths(graph):
    enabled_before = settings.api_rate_limit_enabled
    per_minute_before = settings.api_rate_limit_public_per_minute
    settings.api_rate_limit_enabled = True
    settings.api_rate_limit_public_per_minute = 3
    try:
        with TestClient(app):
            statuses = []
            for _ in range(5):
                # A fresh client per request keeps the identity stable (the
                # session cookie a dev-login sets would change the bucket).
                fresh = TestClient(app)
                statuses.append(fresh.post("/api/auth/dev-login", json={}).status_code)
                fresh.close()
            assert 429 in statuses, "expected the guard to start shedding requests"
    finally:
        settings.api_rate_limit_enabled = enabled_before
        settings.api_rate_limit_public_per_minute = per_minute_before


def test_api_guard_exempts_health(graph):
    with TestClient(app) as client:
        for _ in range(10):
            assert client.get("/api/health").status_code == 200
