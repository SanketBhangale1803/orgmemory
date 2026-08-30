from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.core.config import settings
from app.graph.memory_graph import InMemoryGraphStore, set_graph_store


@pytest.fixture
def graph(tmp_path):
    settings.sqlite_path = tmp_path / "test.db"
    settings.generated_runbooks_dir = tmp_path / "generated"
    store = InMemoryGraphStore()
    set_graph_store(store)
    return store


@pytest.fixture(autouse=True)
def hermetic_deployment_settings(monkeypatch):
    """Keep a developer's deployment .env out of the test environment.

    The root .env legitimately pins production values (FRONTEND_URL,
    PUBLIC_BASE_URL, …) for the hosted deployment. Those values would flip
    cookie flags and redirect targets under the http TestClient, so every
    test starts from local defaults and pins what it actually asserts on.
    """
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
    monkeypatch.setattr(settings, "public_base_url", "")
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "public_demo_mode", False)
    monkeypatch.setattr(settings, "auth_dev_mode", True)
