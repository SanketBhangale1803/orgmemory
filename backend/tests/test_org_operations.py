"""Organizational operations: blockers, conflicts, and the approval boundary.

The scenario is deliberately spread across seven spaces, because the property
worth testing is that no single space answers "are we ready to launch" — the
answer is only correct if the tools connect Product's date, Security's open
review, Infrastructure's deploy dependency, and a meeting note filed in Launch.
"""

import pytest
from fastapi import HTTPException

from app.api.org_routes import (
    approve_plan,
    blockers,
    conflicts,
    dependency_graph,
    list_spaces,
    project_context,
    propose_plan,
    provenance,
    reasoning_chain,
    readiness,
    seed_scenario,
    PlanOperation,
    PlanRequest,
    SeedRequest,
)
from app.auth.app_auth import create_dev_session, create_workspace, issue_session


def _session(email: str, name: str, workspace_name: str) -> str:
    user = create_dev_session(email, name)
    workspace = create_workspace(workspace_name, user["token"])
    return issue_session(user["user"]["id"], workspace["id"])["token"]


@pytest.fixture
def scenario(graph, monkeypatch):
    """Bind the route's services to this test's graph store.

    The route module builds them once at import time, so without this the seed
    writes its documents into whichever store existed then — and every later
    retrieval test in the session silently answers from a launch scenario it
    never asked for.
    """
    from app.api import org_routes
    from app.audit import AuditService
    from app.hcag_adapter import HCAGAdapter
    from app.ingestion import IngestionService
    from app.memory.company import CompanyMemoryService
    from app.orgops import OrgOpsService, WatchService

    memory = CompanyMemoryService(graph)
    monkeypatch.setattr(org_routes, "company_memory", memory)
    monkeypatch.setattr(
        org_routes, "ingestion", IngestionService(graph, HCAGAdapter(graph), AuditService())
    )
    ops = OrgOpsService(memory)
    monkeypatch.setattr(org_routes, "orgops", ops)
    monkeypatch.setattr(org_routes, "watches", WatchService(ops))

    token = _session("launch@orgmemory.local", "Launch Owner", "Launch Co")
    header = f"Bearer {token}"
    seed = seed_scenario(SeedRequest(), authorization=header)
    return header, seed


def test_scenario_spreads_the_answer_across_spaces(scenario):
    header, _ = scenario
    spaces = list_spaces(authorization=header)
    names = {space["name"] for space in spaces["spaces"]}
    assert {"Product", "Engineering", "Security", "Infrastructure", "Launch"} <= names
    # Every space carries memory; a space that answered everything would make
    # the cross-space reconstruction meaningless.
    assert all(space["memory_count"] > 0 for space in spaces["spaces"])


def test_seeding_twice_does_not_duplicate_the_organization(scenario):
    header, first = scenario
    second = seed_scenario(SeedRequest(), authorization=header)
    assert second["created_memories"] == 0
    assert second["created_tasks"] == 0
    assert second["space_ids"] == first["space_ids"]


def test_only_the_root_of_the_stall_is_reported_as_a_blocker(scenario):
    header, _ = scenario
    found = blockers(authorization=header)
    assert found["count"] == 1
    blocker = found["blockers"][0]
    assert blocker["task"]["title"] == "Complete OAuth security approval"
    assert blocker["severity"] == "critical"
    # The deploy is stalled too, but as a consequence — it appears in the chain,
    # never as a second blocker to chase.
    blocked_titles = [task["title"] for task in blocker["blocks"]]
    assert "Promote rc-14 to production" in blocked_titles
    assert "Launch checkout OAuth sign-in" in blocked_titles


def test_conflict_is_anchored_to_the_record_the_task_cites(scenario):
    header, _ = scenario
    found = conflicts(authorization=header)
    assert found["count"] == 1
    conflict = found["conflicts"][0]
    assert conflict["task"]["title"] == "Complete OAuth security approval"
    assert conflict["tracked_state"] == "open"
    assert conflict["source"]["space_name"] == "Launch"
    assert conflict["basis"] == "contradicts"
    # The approval lives in a different space from the tracker it settles.
    assert conflict["tracked_source"]["space_name"] == "Security"


def test_reasoning_chain_returns_the_argument_not_a_result_list(scenario):
    header, _ = scenario
    chain = reasoning_chain(
        topic="why is the security review blocking the production deploy",
        authorization=header,
    )
    titles = [step["memory"]["title"] for step in chain["steps"]]
    assert "External auth changes require a security review" in titles
    assert "Production deployment requires a completed security approval" in titles
    # The policy is the premise, so it must come before the dependency it produced.
    assert titles.index("External auth changes require a security review") < titles.index(
        "Production deployment requires a completed security approval"
    )
    assert chain["edges"]


def test_provenance_opens_a_claim_back_to_its_source(scenario):
    header, _ = scenario
    conflict = conflicts(authorization=header)["conflicts"][0]
    trace = provenance(conflict["source"]["id"], authorization=header)
    assert trace["sources"]
    assert trace["sources"][0]["type"] == "meeting"
    assert any(relation["type"] == "CONTRADICTS" for relation in trace["relations"])


def test_reads_never_change_state_and_writes_wait_for_a_person(scenario):
    header, _ = scenario
    before = readiness(authorization=header)
    assert before["status"] == "NOT READY"

    conflict = conflicts(authorization=header)["conflicts"][0]
    plan = propose_plan(
        PlanRequest(
            space_id=conflict["task"]["space_id"],
            summary="Reconcile the security approval",
            operations=[PlanOperation(**conflict["resolution"])],
        ),
        authorization=header,
    )
    assert plan["status"] == "pending_approval"
    # Proposing is not doing: nothing may have moved yet.
    assert readiness(authorization=header)["status"] == "NOT READY"

    approved = approve_plan(plan["id"], authorization=header)
    assert approved["status"] == "approved"
    assert approved["results"][0]["ok"] is True

    after = readiness(authorization=header)
    assert after["status"] == "READY"
    assert after["blocker_count"] == 0
    states = {entry["label"]: entry["state"] for entry in after["checklist"]}
    assert states["Complete OAuth security approval"] == "done"
    # The deploy has not run, but nothing is holding it any more.
    assert states["Promote rc-14 to production"] == "ready"


def test_another_workspace_cannot_read_this_organization(scenario):
    header, seed = scenario
    outsider = f"Bearer {_session('outsider@orgmemory.local', 'Outsider', 'Other Co')}"
    assert list_spaces(authorization=outsider)["count"] == 0
    with pytest.raises(HTTPException) as error:
        project_context(
            space_ids=seed["space_ids"]["Security"],
            authorization=outsider,
        )
    assert error.value.status_code == 403


def test_dependency_graph_exposes_the_chain_agents_walk(scenario):
    header, _ = scenario
    result = dependency_graph(authorization=header)
    assert result["node_count"] >= 5
    assert result["edge_count"] >= 3
    goal = [node for node in result["nodes"] if node["kind"] == "goal"]
    assert goal and goal[0]["label"] == "Launch checkout OAuth sign-in"


def test_a_watch_finds_the_contradiction_and_drafts_a_fix_without_applying_it(scenario):
    """The autonomous half: nobody asked, and nothing was applied."""
    from app.api.org_routes import (
        WatchRequest,
        create_watch,
        list_watches,
        readiness,
        run_watch,
    )

    header, seed = scenario
    watch = create_watch(
        WatchRequest(
            name="Checkout launch",
            space_ids=list(seed["space_ids"].values()),
            checks=["blockers", "conflicts"],
        ),
        authorization=header,
    )
    result = run_watch(watch["id"], authorization=header)
    kinds = {finding["kind"] for finding in result["findings"]}
    assert {"blocker", "conflict"} <= kinds

    conflict = next(item for item in result["findings"] if item["kind"] == "conflict")
    # A contradiction has one unambiguous fix, so the watch drafts the plan.
    assert conflict["plan_id"]
    # Drafting is not doing.
    assert readiness(authorization=header)["status"] == "NOT READY"

    # Running again must not pile up duplicates of the same situation. A watch
    # that re-drafts the same fix every interval buries the queue it exists to
    # make legible, so the plan count is asserted, not just the finding count.
    from app.api.org_routes import list_plans

    before = len(list_plans(authorization=header)["plans"])
    for _ in range(3):
        second = run_watch(watch["id"], authorization=header)
        assert second["new_findings"] == 0
    assert len(list_plans(authorization=header)["plans"]) == before
    assert len(list_watches(authorization=header)["watches"]) == 1
