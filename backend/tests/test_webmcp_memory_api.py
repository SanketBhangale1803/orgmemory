"""WebMCP organizational-memory API surface: search, related, proposals.

These endpoints back the browser-native WebMCP tools. The invariants under
test are the ones an agent cannot be trusted to enforce itself: workspace and
team isolation, read-only search, and the human approval boundary before
anything is written into durable company memory.
"""

import pytest
from fastapi import HTTPException

from app.api.routes import (
    memory_proposals,
    memory_search,
    memory_unit_related,
    propose_memory,
    resolve_memory_proposal,
)
from app.api.schemas import MemoryProposalRequest, MemoryProposalResolutionRequest
from app.audit import AuditService
from app.auth.app_auth import (
    create_dev_session,
    create_workspace,
    invite_member,
    issue_session,
)
from app.core.database import connect, row
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.memory.company import CompanyMemoryService


def _project(graph, workspace_id: str, name: str) -> str:
    project_id = IngestionService(graph, HCAGAdapter(graph), AuditService()).create_project(name)
    with connect() as conn:
        conn.execute("INSERT INTO workspace_projects VALUES (?,?)", (workspace_id, project_id))
    return project_id


def _workspace_session(email: str, name: str, workspace_name: str) -> dict:
    """A dev user bound to its own workspace, the way a real sign-in lands."""
    user = create_dev_session(email, name)
    workspace = create_workspace(workspace_name, user["token"])
    session = issue_session(user["user"]["id"], workspace["id"])
    assert session["user"]["active_workspace_id"] == workspace["id"]
    return {
        "token": session["token"],
        "workspace_id": workspace["id"],
        "user_id": user["user"]["id"],
    }


def _seed_payment_history(graph, project_id: str) -> None:
    service = CompanyMemoryService(graph)
    service.create(
        project_id,
        "incident",
        "payments outage",
        "Payments failed with PostgreSQL connection-pool exhaustion after the worker concurrency change.",
        ["src_1"],
        0.9,
        {"project": project_id, "service": "payments"},
    )
    service.create(
        project_id,
        "incident",
        "payments degraded checkout",
        "Checkout timed out because payments exhausted its connection pool during a batch job.",
        ["src_2"],
        0.88,
        {"project": project_id, "service": "payments"},
    )
    service.create(
        project_id,
        "decision",
        "payments connection pool",
        "The team decided to cap payments worker concurrency to protect the PostgreSQL pool.",
        ["src_3"],
        0.92,
        {"project": project_id, "service": "payments"},
    )
    service.create(
        project_id,
        "dependency",
        "payments database",
        "Payments depends on the shared PostgreSQL cluster and the ledger service.",
        ["src_4"],
        0.9,
        {"project": project_id, "service": "payments"},
    )


def test_memory_search_finds_incidents_and_decisions(graph):
    owner = _workspace_session("search-owner@example.com", "Search Owner", "Search Workspace")
    project_id = _project(graph, owner["workspace_id"], "Search project")
    _seed_payment_history(graph, project_id)

    results = memory_search(
        q="payments connection pool",
        project_id="",
        type="",
        limit=10,
        authorization=f"Bearer {owner['token']}",
    )

    assert results["searched_projects"] >= 1
    subjects = [item["subject"] for item in results["results"]]
    assert "payments outage" in subjects
    assert "payments connection pool" in subjects
    top = results["results"][0]
    assert top["project_id"] == project_id
    assert top["project_name"] == "Search project"
    assert top["scope"]["service"] == "payments"

    by_type = memory_search(
        q="payments",
        project_id=project_id,
        type="incident",
        limit=10,
        authorization=f"Bearer {owner['token']}",
    )
    assert {item["type"] for item in by_type["results"]} == {"incident"}
    assert len(by_type["results"]) == 2


def test_memory_search_is_workspace_isolated(graph):
    owner = _workspace_session(
        "isolation-owner@example.com", "Isolation Owner", "Isolation Workspace"
    )
    project_id = _project(graph, owner["workspace_id"], "Isolation project")
    _seed_payment_history(graph, project_id)

    stranger = _workspace_session(
        "stranger-owner@example.com", "Stranger Owner", "Stranger Workspace"
    )

    results = memory_search(
        q="payments connection pool",
        project_id="",
        type="",
        limit=50,
        authorization=f"Bearer {stranger['token']}",
    )
    assert results["results"] == []

    with pytest.raises(HTTPException) as exc:
        memory_search(
            q="payments",
            project_id=project_id,
            type="",
            limit=10,
            authorization=f"Bearer {stranger['token']}",
        )
    assert exc.value.status_code == 403


def test_memory_search_requires_authentication(graph):
    with pytest.raises(HTTPException) as exc:
        memory_search(q="payments", project_id="", type="", limit=10, authorization=None)
    assert exc.value.status_code == 401


def test_related_memories_follow_relationships_and_subject(graph):
    owner = _workspace_session("related-owner@example.com", "Related Owner", "Related Workspace")
    project_id = _project(graph, owner["workspace_id"], "Related project")
    service = CompanyMemoryService(graph)
    old = service.create(
        project_id,
        "fact",
        "payments workers",
        "Payments runs 16 workers.",
        ["a"],
        0.8,
        {"project": project_id, "service": "payments"},
    )
    new = service.create(
        project_id,
        "fact",
        "payments workers",
        "Payments now runs 4 workers to protect the database pool.",
        ["b"],
        0.9,
        {"project": project_id, "service": "payments"},
    )

    related = memory_unit_related(new["id"], authorization=f"Bearer {owner['token']}")
    entries = {entry["memory"]["id"]: entry for entry in related["related"]}
    assert old["id"] in entries
    assert entries[old["id"]]["relationship"] in {"UPDATES", "SAME_SUBJECT"}
    assert entries[old["id"]]["memory"]["subject"] == "payments workers"


def test_memory_proposal_stays_pending_until_an_admin_approves(graph):
    owner = _workspace_session("proposal-owner@example.com", "Proposal Owner", "Proposal Workspace")
    project_id = _project(graph, owner["workspace_id"], "Proposal project")

    proposal = propose_memory(
        MemoryProposalRequest(
            project_id=project_id,
            kind="incident",
            subject="payments outage recurrence",
            content="Payments failed again with pool exhaustion; matches the 2026-06 incident.",
            service="payments",
            reason="Corroborated by monitoring evidence during the current session.",
        ),
        authorization=f"Bearer {owner['token']}",
    )
    assert proposal["status"] == "pending_approval"

    # Nothing may be persisted before a human decision.
    assert (
        row(
            "SELECT COUNT(*) AS n FROM memory_units WHERE project_id=? AND subject=?",
            (project_id, "payments outage recurrence"),
        )["n"]
        == 0
    )

    # An identical proposal is idempotent instead of duplicating the queue.
    duplicate = propose_memory(
        MemoryProposalRequest(
            project_id=project_id,
            kind="incident",
            subject="payments outage recurrence",
            content="Payments failed again with pool exhaustion; matches the 2026-06 incident.",
            service="payments",
            reason="Repeated by a second agent pass.",
        ),
        authorization=f"Bearer {owner['token']}",
    )
    assert duplicate["id"] == proposal["id"]

    resolved = resolve_memory_proposal(
        proposal["id"],
        MemoryProposalResolutionRequest(approved=True),
        authorization=f"Bearer {owner['token']}",
    )
    assert resolved["status"] == "approved"
    assert resolved["memory_id"].startswith("mem_")

    stored = row("SELECT * FROM memory_units WHERE id=?", (resolved["memory_id"],))
    assert stored["type"] == "incident"
    assert stored["is_latest"] == 1

    denied = propose_memory(
        MemoryProposalRequest(
            project_id=project_id,
            kind="decision",
            subject="payments rollback policy",
            content="Roll back payments on any pool exhaustion alert.",
            service="payments",
        ),
        authorization=f"Bearer {owner['token']}",
    )
    resolve_memory_proposal(
        denied["id"],
        MemoryProposalResolutionRequest(approved=False),
        authorization=f"Bearer {owner['token']}",
    )
    assert (
        row("SELECT status FROM memory_proposals WHERE id=?", (denied["id"],))["status"] == "denied"
    )
    assert (
        row(
            "SELECT COUNT(*) AS n FROM memory_units WHERE project_id=? AND subject=?",
            (project_id, "payments rollback policy"),
        )["n"]
        == 0
    )


def test_memory_proposals_are_invisible_to_other_workspaces_and_members_cannot_resolve(graph):
    owner = _workspace_session("boundary-owner@example.com", "Boundary Owner", "Boundary Workspace")
    project_id = _project(graph, owner["workspace_id"], "Boundary project")
    invite_member(owner["workspace_id"], "colleague@example.com", "member")
    with connect() as conn:
        # An invited membership becomes active on first sign-in; mirror that.
        conn.execute(
            "UPDATE workspace_members SET status='active' WHERE workspace_id=? AND user_id=?",
            (
                owner["workspace_id"],
                row("SELECT id FROM users WHERE email=?", ("colleague@example.com",))["id"],
            ),
        )
    colleague = issue_session(
        row("SELECT id FROM users WHERE email=?", ("colleague@example.com",))["id"],
        owner["workspace_id"],
    )

    proposal = propose_memory(
        MemoryProposalRequest(
            project_id=project_id,
            kind="fact",
            subject="payments on-call rotation",
            content="The payments rotation pages the platform team first.",
            service="payments",
        ),
        authorization=f"Bearer {owner['token']}",
    )

    # The proposing owner sees the proposal in the workspace queue.
    visible = memory_proposals(status="", authorization=f"Bearer {owner['token']}")
    assert any(item["id"] == proposal["id"] for item in visible)

    stranger = _workspace_session(
        "boundary-stranger@example.com", "Boundary Stranger", "Boundary Other"
    )
    assert memory_proposals(status="", authorization=f"Bearer {stranger['token']}") == []

    # A member of the same workspace can propose but can never approve.
    member_proposal = propose_memory(
        MemoryProposalRequest(
            project_id=project_id,
            kind="fact",
            subject="payments escalation path",
            content="Escalations for payments start with the on-call engineer.",
            service="payments",
        ),
        authorization=f"Bearer {colleague['token']}",
    )
    assert member_proposal["status"] == "pending_approval"
    with pytest.raises(HTTPException) as exc:
        resolve_memory_proposal(
            member_proposal["id"],
            MemoryProposalResolutionRequest(approved=True),
            authorization=f"Bearer {colleague['token']}",
        )
    assert exc.value.status_code == 403

    with pytest.raises(HTTPException) as exc:
        propose_memory(
            MemoryProposalRequest(
                project_id=project_id,
                kind="fact",
                subject="unauthorized write",
                content="A stranger must not be able to propose into this project.",
            ),
            authorization=f"Bearer {stranger['token']}",
        )
    assert exc.value.status_code == 403
