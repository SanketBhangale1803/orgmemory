"""Create the Phase 3 semantic-change demo from real persisted belief records.

Usage:
    GRAPH_BACKEND=memory .venv/bin/python -m scripts.demo_semantic_change SAP-AI-PRs
"""

from __future__ import annotations

import sys

from app.core.database import init_db, row
from app.graph.memory_graph import InMemoryGraphStore
from app.memory import BeliefStore, ChangeIntelligenceService

ENTRA_DIFF = """diff --git a/src/main.jsx b/src/main.jsx
--- a/src/main.jsx
+++ b/src/main.jsx
@@ -12,8 +12,8 @@
-const employeeDirectory = localEmployeeFixture;
-const employee = employeeDirectory.find(item => item.id === employeeId);
+const entraIdClient = createEntraIdClient();
+const employee = await entraIdClient.getUser(ssoClaims.employeeId);
"""


def main(project_query: str) -> str:
    init_db()
    project = row(
        "SELECT * FROM projects WHERE lower(name) LIKE ? ORDER BY created_at DESC LIMIT 1",
        (f"%{project_query.casefold()}%",),
    )
    if not project:
        raise SystemExit(f"No project matched {project_query!r}")

    graph = InMemoryGraphStore()
    beliefs = BeliefStore(graph)
    service = ChangeIntelligenceService(graph)
    repository = str(project.get("repository") or project["name"])
    repository = repository.removeprefix("https://github.com/").removesuffix(".git")
    scope = {"project": project["id"], "repo": repository}
    event, created = service.observe(
        project["id"],
        f"demo-entra-migration-v3:{project['id']}",
        "github_push",
        repository,
        "b84352225282347b52d3fe83556b300de252791f",
        f"https://github.com/{repository}/commit/b84352225282347b52d3fe83556b300de252791f",
        {"demo": True},
    )
    if not created:
        return event["id"]

    source = {
        "type": "repo_file",
        "id": "file:src/main.jsx@before-entra",
        "timestamp": "2026-07-20T10:00:00Z",
        "confidence": 0.95,
        "metadata": {"title": "src/main.jsx", "repository": repository},
    }
    for claim, value in (
        (
            "employee identity source",
            "Employee identity comes from a local employee directory fixture.",
        ),
        (
            "local employee directory fixture",
            "The application uses a local employee directory fixture.",
        ),
    ):
        current = beliefs.get_current(project["id"], claim, scope)
        if not current or current["current_value"].casefold() != value.casefold():
            beliefs.create(
                project["id"],
                claim,
                value,
                confidence=0.93,
                scope=scope,
                authority_tier="current_code_config",
                source=source,
            )

    result = service.process(event["id"], ENTRA_DIFF, {"scope": scope})
    return str((result or event)["id"])


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "SAP-AI-PRs"))
