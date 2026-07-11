from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph import get_graph_store

if __name__ == "__main__":
    store = get_graph_store()
    store.initialize()
    print(store.health())
