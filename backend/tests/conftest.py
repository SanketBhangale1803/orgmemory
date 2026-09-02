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

    LLM credentials are cleared for the same reason: with a real key present,
    every ask-path test silently fired live provider calls (minutes of network
    latency per test, non-deterministic answers, and real API spend). With no
    key configured, generate_grounded_json() returns None and the answer path
    stays local and deterministic — which is what these tests assert against.
    """
    monkeypatch.setattr(settings, "frontend_url", "http://localhost:3000")
    monkeypatch.setattr(settings, "public_base_url", "")
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "public_demo_mode", False)
    monkeypatch.setattr(settings, "auth_dev_mode", True)
    for key in (
        "openai_api_key",
        "anthropic_api_key",
        "google_api_key",
        "openrouter_api_key",
        "xai_api_key",
        "kimi_api_key",
    ):
        monkeypatch.setattr(settings, key, "")
    monkeypatch.setattr(settings, "org_memory_default_model_provider", "none")
    monkeypatch.setattr(settings, "org_memory_answer_candidates", 1)
    monkeypatch.setattr(settings, "org_memory_answer_judge_enabled", False)
