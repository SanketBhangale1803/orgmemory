from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.graph import get_graph_store

if __name__ == "__main__":
    try:
        get_graph_store().reset()
    except Exception as exc:
        print(f"Graph reset skipped: {exc}")
    settings.sqlite_path.unlink(missing_ok=True)
    shutil.rmtree(settings.generated_runbooks_dir, ignore_errors=True)
    shutil.rmtree(settings.repo_cache_dir, ignore_errors=True)
    print("Runbook application data reset.")
