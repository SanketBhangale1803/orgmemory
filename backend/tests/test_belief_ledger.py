from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory import BeliefStore


def _project(graph):
    return IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(
        "Belief ledger"
    )


def _source(source_id: str, timestamp: str = "2026-07-20T12:00:00Z"):
    return {
        "type": "repo_file",
        "id": source_id,
        "timestamp": timestamp,
        "confidence": 0.96,
        "metadata": {"title": "src/main.jsx"},
    }


def test_updating_belief_preserves_prior_data_and_builds_traversable_chain(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id, "repo": "acme/app", "service": "identity"}
    first = store.create(
        project_id,
        "employee identity source",
        "Employee identity comes from a local fixture.",
        confidence=0.9,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("file:fixture"),
    )
    second = store.update(
        first["id"],
        "Employee identity comes from Microsoft Entra ID.",
        relationship="UPDATES",
        source=_source("commit:entra", "2026-07-21T12:00:00Z"),
    )
    third = store.update(
        second["current"]["id"],
        "Employee identity comes from Microsoft Entra ID through SSO claims.",
        relationship="UPDATES",
        source=_source("commit:sso", "2026-07-22T12:00:00Z"),
    )

    history = store.get_history(first["id"])

    assert [item["current_value"] for item in history["beliefs"]] == [
        "Employee identity comes from a local fixture.",
        "Employee identity comes from Microsoft Entra ID.",
        "Employee identity comes from Microsoft Entra ID through SSO claims.",
    ]
    assert [item["relationship"] for item in history["relationships"]] == [
        "UPDATES",
        "UPDATES",
    ]
    assert history["relationships"][0]["from_belief_id"] == first["id"]
    assert history["relationships"][0]["to_belief_id"] == second["current"]["id"]
    assert store.get(first["id"])["status"] == "updated"
    assert store.get(first["id"])["supporting_sources"][0]["source_id"] == "file:fixture"
    assert (
        store.get_current(project_id, "employee identity source", scope)["id"]
        == third["current"]["id"]
    )


def test_invalidation_is_append_only_and_removes_claim_from_current_view(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id, "repo": "acme/app"}
    first = store.create(
        project_id,
        "local employee fixture",
        "The application uses a local employee directory fixture.",
        confidence=0.91,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("file:fixture"),
    )

    invalidated = store.update(
        first["id"],
        "The local employee directory fixture is no longer authoritative.",
        relationship="INVALIDATES",
        source=_source("commit:entra", "2026-07-21T12:00:00Z"),
    )

    assert store.get(first["id"])["status"] == "invalidated"
    assert invalidated["current"]["status"] == "invalidated"
    assert store.get_current(project_id, "local employee fixture", scope) is None
    assert len(store.get_history(first["id"])["beliefs"]) == 2
    assert graph.list_edges(project_id, "INVALIDATES", 10)


def test_replaying_same_evidence_does_not_duplicate_belief_or_provenance(graph):
    project_id = _project(graph)
    store = BeliefStore(graph)
    scope = {"project": project_id}
    first = store.create(
        project_id,
        "identity provider",
        "Microsoft Entra ID is the identity provider.",
        confidence=0.95,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("commit:entra"),
    )
    replay = store.create(
        project_id,
        "identity provider",
        "Microsoft Entra ID is the identity provider.",
        confidence=0.95,
        scope=scope,
        authority_tier="current_code_config",
        source=_source("commit:entra"),
    )

    assert replay["id"] == first["id"]
    assert len(store.evidence(first["id"])) == 1
