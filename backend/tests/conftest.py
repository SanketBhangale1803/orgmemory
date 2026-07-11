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
