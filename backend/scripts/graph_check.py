from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.graph import get_graph_store


def main() -> None:
    graph = get_graph_store()
    print(json.dumps(graph.health(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
