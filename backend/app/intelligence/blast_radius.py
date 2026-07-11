"""Blast-radius analysis over the real project graph.

All statements are generated from edges that ingestion actually created:
SERVICE_DEPENDS_ON_SERVICE, SERVICE_USES_ENV_VAR, SERVICE_DEFINED_IN_FILE,
SERVICE_HAS_DOCKER_CONFIG, RUNBOOK_APPLIES_TO_SERVICE, and
SERVICE_OWNED_BY. If the graph holds no relevant edges, the report says so
instead of inventing impact.
"""

from __future__ import annotations

from typing import Any

from app.graph.base import GraphStore


def _suffix(node_id: Any) -> str:
    return str(node_id).split(":")[-1]


def blast_radius(graph: GraphStore, project_id: str, service_name: str) -> dict[str, Any]:
    service_id = f"{project_id}:{service_name.lower()}"
    edges = graph.list_edges(project_id, limit=5000)

    dependencies: set[str] = set()
    dependents: set[str] = set()
    env_vars: set[str] = set()
    defined_in: set[str] = set()
    docker_configs: set[str] = set()
    runbooks: set[str] = set()
    owners: set[str] = set()

    for edge in edges:
        relationship = edge.get("relationship")
        from_id, to_id = edge.get("from_id"), edge.get("to_id")
        if relationship == "SERVICE_DEPENDS_ON_SERVICE":
            if from_id == service_id:
                dependencies.add(_suffix(to_id))
            elif to_id == service_id:
                dependents.add(_suffix(from_id))
        elif relationship == "SERVICE_USES_ENV_VAR" and from_id == service_id:
            env_vars.add(_suffix(to_id))
        elif relationship == "SERVICE_DEFINED_IN_FILE" and from_id == service_id:
            defined_in.add(_suffix(to_id))
        elif relationship == "SERVICE_HAS_DOCKER_CONFIG" and from_id == service_id:
            docker_configs.add(_suffix(to_id))
        elif relationship == "RUNBOOK_APPLIES_TO_SERVICE" and to_id == service_id:
            runbooks.add(str(from_id))
        elif relationship == "SERVICE_OWNED_BY" and from_id == service_id:
            owners.add(_suffix(to_id))

    # Second hop: services that depend on the direct dependents are also in
    # the radius. One extra hop keeps the report interpretable.
    second_hop: set[str] = set()
    dependent_ids = {f"{project_id}:{name}" for name in dependents}
    for edge in edges:
        if (
            edge.get("relationship") == "SERVICE_DEPENDS_ON_SERVICE"
            and edge.get("to_id") in dependent_ids
        ):
            name = _suffix(edge.get("from_id"))
            if name != service_name.lower() and name not in dependents:
                second_hop.add(name)

    impact: list[str] = []
    if dependents:
        impact.append(
            f"Restarting or breaking {service_name} may affect downstream service(s): "
            f"{', '.join(sorted(dependents))}."
        )
    if second_hop:
        impact.append(
            f"Second-hop dependents that could be indirectly affected: {', '.join(sorted(second_hop))}."
        )
    if env_vars:
        impact.append(
            f"Changing env var(s) {', '.join(sorted(env_vars))} may break {service_name}."
        )
    if dependencies:
        impact.append(
            f"{service_name} depends on {', '.join(sorted(dependencies))}; outages there propagate here."
        )
    if not impact:
        impact.append(
            f"The graph holds no dependency edges for {service_name}; blast radius is unknown, "
            "not zero. Ingest compose files, workflows, or issue history to populate it."
        )

    return {
        "project_id": project_id,
        "service_name": service_name,
        "dependencies": sorted(dependencies),
        "direct_dependents": sorted(dependents),
        "second_hop_dependents": sorted(second_hop),
        "env_vars": sorted(env_vars),
        "defined_in_files": sorted(defined_in),
        "docker_configs": sorted(docker_configs),
        "applicable_runbooks": sorted(runbooks),
        "owners": sorted(owners),
        "impact_statements": impact,
        "basis": "graph_edges_only",
    }
