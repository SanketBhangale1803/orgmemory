from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .config import settings


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:20]}"


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, repository TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
  auth_provider TEXT NOT NULL, external_id TEXT NOT NULL, role_hint TEXT NOT NULL DEFAULT 'member',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspaces (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, slug TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS workspace_members (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, user_id TEXT NOT NULL,
  role TEXT NOT NULL, status TEXT NOT NULL, invited_email TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(workspace_id, user_id),
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS workspace_projects (
  workspace_id TEXT NOT NULL, project_id TEXT NOT NULL,
  PRIMARY KEY(workspace_id, project_id),
  FOREIGN KEY(workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
  expires_at TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS knowledge_items (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, source_type TEXT NOT NULL,
  source_id TEXT NOT NULL, source_title TEXT NOT NULL, source_url TEXT NOT NULL,
  content TEXT NOT NULL, metadata_json TEXT NOT NULL, created_at TEXT NOT NULL,
  FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS runbooks (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, runbook_key TEXT NOT NULL,
  name TEXT NOT NULL, description TEXT NOT NULL, risk_level TEXT NOT NULL,
  confidence REAL NOT NULL, yaml_path TEXT NOT NULL, json_path TEXT NOT NULL,
  payload_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(project_id, runbook_key), FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, runbook_id TEXT NOT NULL,
  step_id TEXT NOT NULL, action_type TEXT NOT NULL, summary TEXT NOT NULL,
  command_preview TEXT NOT NULL, params_json TEXT NOT NULL, decision TEXT NOT NULL,
  status TEXT NOT NULL, reason TEXT NOT NULL, risk_score INTEGER NOT NULL,
  requested_at TEXT NOT NULL, resolved_at TEXT, resolved_by TEXT
);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY, project_id TEXT, event_type TEXT NOT NULL, actor TEXT NOT NULL,
  summary TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS connector_accounts (
  id TEXT PRIMARY KEY, provider TEXT NOT NULL, external_id TEXT NOT NULL,
  display_name TEXT NOT NULL, status TEXT NOT NULL, secret_encrypted TEXT NOT NULL,
  metadata_json TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(provider, external_id)
);
CREATE TABLE IF NOT EXISTS oauth_states (
  state TEXT PRIMARY KEY, provider TEXT NOT NULL, expires_at TEXT NOT NULL, used_at TEXT
);
CREATE TABLE IF NOT EXISTS ingestion_jobs (
  id TEXT PRIMARY KEY, project_id TEXT, workspace_id TEXT, source TEXT NOT NULL,
  source_ref TEXT NOT NULL, status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
  files_scanned INTEGER NOT NULL DEFAULT 0, issues_scanned INTEGER NOT NULL DEFAULT 0,
  pull_requests_scanned INTEGER NOT NULL DEFAULT 0, knowledge_items_created INTEGER NOT NULL DEFAULT 0,
  knowledge_chunks_created INTEGER NOT NULL DEFAULT 0, graph_nodes_created INTEGER NOT NULL DEFAULT 0,
  graph_edges_created INTEGER NOT NULL DEFAULT 0, warnings_json TEXT NOT NULL DEFAULT '[]',
  error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  completed_at TEXT
);
CREATE TABLE IF NOT EXISTS operational_memories (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, statement TEXT NOT NULL,
  memory_type TEXT NOT NULL, scope TEXT NOT NULL DEFAULT 'project',
  owner TEXT NOT NULL DEFAULT '', approval_policy TEXT NOT NULL DEFAULT '',
  confidence REAL NOT NULL, status TEXT NOT NULL,
  source_item_ids_json TEXT NOT NULL DEFAULT '[]',
  evidence_json TEXT NOT NULL DEFAULT '[]',
  last_verified TEXT NOT NULL, approved_by TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS operational_assertions (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL, claim TEXT NOT NULL,
  subject_type TEXT NOT NULL, subject_id TEXT NOT NULL, environment_scope TEXT NOT NULL DEFAULT 'unknown',
  status TEXT NOT NULL, confidence REAL NOT NULL, trust_score REAL NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_verified_at TEXT,
  valid_from TEXT, valid_to TEXT, source_version TEXT NOT NULL DEFAULT '', commit_sha TEXT NOT NULL DEFAULT '',
  source_updated_at TEXT, verification_owner TEXT NOT NULL DEFAULT '', verification_reason TEXT NOT NULL DEFAULT '',
  evidence_json TEXT NOT NULL DEFAULT '[]', affected_runbook_ids_json TEXT NOT NULL DEFAULT '[]',
  affected_runbook_step_ids_json TEXT NOT NULL DEFAULT '[]', approval_requirement TEXT NOT NULL DEFAULT 'human_review_required',
  policy_status TEXT NOT NULL DEFAULT 'unverified'
);
CREATE TABLE IF NOT EXISTS change_impacts (
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, change_type TEXT NOT NULL, change_ref TEXT NOT NULL,
  status TEXT NOT NULL, severity TEXT NOT NULL, summary TEXT NOT NULL, payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS api_keys (
  id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL DEFAULT '', name TEXT NOT NULL,
  key_prefix TEXT NOT NULL, key_hash TEXT NOT NULL UNIQUE,
  created_by TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
  last_used_at TEXT, revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_project ON knowledge_items(project_id);
CREATE INDEX IF NOT EXISTS idx_memories_project ON operational_memories(project_id, status);
CREATE INDEX IF NOT EXISTS idx_assertions_project ON operational_assertions(project_id, status, updated_at);
CREATE INDEX IF NOT EXISTS idx_assertions_subject ON operational_assertions(project_id, subject_type, subject_id);
CREATE INDEX IF NOT EXISTS idx_impacts_project ON change_impacts(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runbooks_project ON runbooks(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_project ON audit_events(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_project ON ingestion_jobs(project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_workspace_members ON workspace_members(workspace_id, user_id);
"""


def init_db() -> None:
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(settings.sqlite_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    init_db()
    conn = sqlite3.connect(settings.sqlite_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def rows(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def row(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    result = rows(sql, params)
    return result[0] if result else None


def decode(record: dict[str, Any]) -> dict[str, Any]:
    output = dict(record)
    for key in list(output):
        if key.endswith("_json"):
            output[key.removesuffix("_json")] = json.loads(output.pop(key) or "{}")
    return output
