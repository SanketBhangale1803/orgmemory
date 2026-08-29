"""A realistic multi-space organization for the WebMCP walkthrough.

The point of the scenario is that no single space contains the answer. Product
knows the date, Security knows a review is open, Infrastructure knows the deploy
depends on that review, and the approval that would unblock everything is buried
in a meeting note in a fourth space. A person reconstructs that by opening all of
them. An agent reconstructs it with four tool calls.

Seeding is idempotent: running it twice reuses the same spaces, memories, and
tasks rather than producing a second copy of the organization.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.core.database import connect, new_id, row, rows, utcnow

SPACES = [
    ("Product", "What we are shipping and when."),
    ("Engineering", "Build, test, and release state."),
    ("Design", "Interface decisions and approvals."),
    ("Security", "Reviews, approvals, and policy."),
    ("Infrastructure", "Deployment and environment dependencies."),
    ("Launch", "Launch coordination, checklists, and sync notes."),
    ("Customer Support", "Readiness for customer-facing change."),
]


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat()


def _memory_plan(now: datetime) -> list[dict]:
    """Every seeded memory, with the timestamp that makes the story legible."""
    day = timedelta(days=1)
    return [
        # ---------------------------------------------------------- Product
        {
            "space": "Product",
            "type": "policy",
            "subject": "Checkout OAuth sign-in launches Friday 09:00 UTC",
            "content": (
                "Checkout OAuth sign-in is scheduled to go live Friday at 09:00 UTC. "
                "The date was committed to the two enterprise design partners."
            ),
            "at": now - 9 * day,
            "source": ("document", "Q3 launch plan"),
        },
        {
            "space": "Product",
            "type": "decision",
            "subject": "Feature freeze for the OAuth launch is in effect",
            "content": (
                "No further scope is accepted for the OAuth sign-in release. "
                "Only defect fixes and release-blocking work go in."
            ),
            "at": now - 4 * day,
            "source": ("meeting", "Product review"),
        },
        {
            "space": "Product",
            "type": "open_question",
            "subject": "Announcement scope for OAuth sign-in is undecided",
            "content": (
                "Undecided whether OAuth sign-in is announced to all customers on day one "
                "or rolled out to the design partners first."
            ),
            "at": now - 2 * day,
            "source": ("message", "#product"),
        },
        # ------------------------------------------------------ Engineering
        {
            "space": "Engineering",
            "type": "fact",
            "subject": "Backend release candidate rc-14 is deployed to staging",
            "content": (
                "rc-14 carries the OAuth token exchange and is running on staging. "
                "Integration and load suites passed on the second run."
            ),
            "at": now - 3 * day,
            "source": ("document", "CI run 8841"),
        },
        {
            "space": "Engineering",
            "type": "decision",
            "subject": "Production deploy waits for the security sign-off",
            "content": (
                "Engineering will not promote rc-14 to production until the security "
                "review for the external auth surface is recorded as complete."
            ),
            "at": now - 3 * day,
            "source": ("meeting", "Release readiness sync"),
        },
        {
            "space": "Engineering",
            "type": "ownership",
            "subject": "Checkout backend ownership",
            "content": "The checkout backend service is owned by Priya Raman.",
            "at": now - 30 * day,
            "source": ("document", "Service catalog"),
        },
        {
            "space": "Engineering",
            "type": "incident",
            "subject": "staging OAuth callback redirect loop",
            "content": (
                "OAuth callbacks looped on staging for 90 minutes after a mismatched "
                "redirect URI. Fixed by pinning the callback host per environment."
            ),
            "at": now - 11 * day,
            "source": ("document", "Incident 214 postmortem"),
        },
        # ----------------------------------------------------------- Design
        {
            "space": "Design",
            "type": "decision",
            "subject": "Final OAuth sign-in interface is approved",
            "content": (
                "The sign-in screen, provider chooser, and error states are approved as of "
                "the design review. No further visual changes before launch."
            ),
            "at": now - 5 * day,
            "source": ("meeting", "Design review"),
        },
        {
            "space": "Design",
            "type": "ownership",
            "subject": "Checkout design ownership",
            "content": "Checkout interface design is owned by Marco Silva.",
            "at": now - 30 * day,
            "source": ("document", "Team directory"),
        },
        # --------------------------------------------------------- Security
        {
            "space": "Security",
            "type": "policy",
            "subject": "External auth changes require a security review",
            "content": (
                "Any change that alters an externally reachable authentication surface "
                "requires a recorded security review before it reaches production."
            ),
            "at": now - 60 * day,
            "source": ("document", "Security policy 4.2"),
        },
        {
            "space": "Security",
            "type": "open_question",
            "subject": "OAuth security review is still open in the security tracker",
            "content": (
                "The OAuth security review was requested for the checkout sign-in change. "
                "The tracker still shows it awaiting approval."
            ),
            "at": now - 3 * day,
            "source": ("document", "Security tracker SR-118"),
        },
        {
            "space": "Security",
            "type": "ownership",
            "subject": "Security review ownership",
            "content": "Security reviews for checkout are owned by Dana Whitfield.",
            "at": now - 30 * day,
            "source": ("document", "Team directory"),
        },
        # --------------------------------------------------- Infrastructure
        {
            "space": "Infrastructure",
            "type": "dependency",
            "subject": "Production deployment requires a completed security approval",
            "content": (
                "The production deploy pipeline for checkout is gated on a completed "
                "security approval for the change being promoted."
            ),
            "at": now - 45 * day,
            "source": ("document", "Deploy pipeline policy"),
        },
        {
            "space": "Infrastructure",
            "type": "fact",
            "subject": "Deploy pipeline is healthy",
            "content": (
                "The checkout deploy pipeline is green. The last successful production "
                "deploy completed six days ago with no rollback."
            ),
            "at": now - 1 * day,
            "source": ("document", "Deploy dashboard"),
        },
        {
            "space": "Infrastructure",
            "type": "ownership",
            "subject": "Production deploy ownership",
            "content": "Production deploys for checkout are owned by Sam Okafor.",
            "at": now - 30 * day,
            "source": ("document", "Service catalog"),
        },
        # ----------------------------------------------------------- Launch
        {
            "space": "Launch",
            "type": "fact",
            "subject": "Launch checklist for checkout OAuth",
            "content": (
                "The launch checklist tracks four gates: design approval, backend testing, "
                "security approval, and the production deploy."
            ),
            "at": now - 6 * day,
            "source": ("document", "Launch checklist"),
        },
        # The approval that already happened. It lives in a meeting note, in a
        # different space from the tracker that still says the review is open.
        {
            "space": "Launch",
            "type": "decision",
            "subject": "OAuth security review approved for Friday release",
            "content": (
                "Dana Whitfield in the Thursday release sync: the OAuth review looks good "
                "from my side, approved for the Friday release. No follow-up items."
            ),
            "at": (now - day).replace(hour=15, minute=42, second=0, microsecond=0),
            "source": ("meeting", "Thursday release sync"),
        },
        {
            "space": "Launch",
            "type": "open_question",
            "subject": "Friday morning launch comms owner is unassigned",
            "content": "Nobody has taken the Friday 09:00 announcement and status page update.",
            "at": now - 2 * day,
            "source": ("message", "#launch"),
        },
        # -------------------------------------------------- Customer Support
        {
            "space": "Customer Support",
            "type": "fact",
            "subject": "Support macros for OAuth sign-in errors are drafted",
            "content": (
                "Draft macros cover provider timeouts, denied consent, and account linking. "
                "They have not been reviewed by the checkout team."
            ),
            "at": now - 2 * day,
            "source": ("document", "Support macro draft"),
        },
        {
            "space": "Customer Support",
            "type": "open_question",
            "subject": "Support has not been briefed on the OAuth rollback path",
            "content": (
                "If sign-in is rolled back mid-launch, support does not have a documented "
                "answer for customers already migrated."
            ),
            "at": now - 1 * day,
            "source": ("message", "#support"),
        },
    ]


def _task_plan(now: datetime) -> list[dict]:
    day = timedelta(days=1)
    return [
        {
            "key": "design_approval",
            "space": "Design",
            "title": "Approve final sign-in interface",
            "description": "Sign off the sign-in screen, provider chooser, and error states.",
            "status": "done",
            "owner": "Marco Silva",
            "priority": "high",
            "kind": "gate",
            "depends_on": [],
            "evidence": ["Final OAuth sign-in interface is approved"],
            "at": now - 5 * day,
        },
        {
            "key": "backend_testing",
            "space": "Engineering",
            "title": "Test backend release candidate rc-14",
            "description": "Integration and load suites against the OAuth token exchange.",
            "status": "done",
            "owner": "Priya Raman",
            "priority": "high",
            "kind": "gate",
            "depends_on": [],
            "evidence": ["Backend release candidate rc-14 is deployed to staging"],
            "at": now - 3 * day,
        },
        {
            "key": "security_approval",
            "space": "Security",
            "title": "Complete OAuth security approval",
            "description": (
                "Record the security review outcome for the external OAuth sign-in surface."
            ),
            "status": "open",
            "owner": "Dana Whitfield",
            "priority": "critical",
            "kind": "gate",
            "depends_on": [],
            "evidence": [
                "OAuth security review is still open in the security tracker",
                "External auth changes require a security review",
            ],
            # Two days old, so the Thursday meeting decision is unambiguously newer.
            "at": now - 2 * day,
        },
        {
            "key": "production_deploy",
            "space": "Infrastructure",
            "title": "Promote rc-14 to production",
            "description": "Run the checkout deploy pipeline against the release candidate.",
            "status": "blocked",
            "owner": "Sam Okafor",
            "priority": "critical",
            "kind": "step",
            "depends_on": ["backend_testing", "security_approval"],
            "evidence": ["Production deployment requires a completed security approval"],
            "at": now - 2 * day,
        },
        {
            "key": "launch_goal",
            "space": "Launch",
            "title": "Launch checkout OAuth sign-in",
            "description": "Friday 09:00 UTC go-live for OAuth sign-in on checkout.",
            "status": "blocked",
            "owner": "Priya Raman",
            "priority": "critical",
            "kind": "goal",
            "depends_on": ["design_approval", "production_deploy"],
            "evidence": ["Checkout OAuth sign-in launches Friday 09:00 UTC"],
            "at": now - 6 * day,
        },
        {
            "key": "support_rollback",
            "space": "Customer Support",
            "title": "Document the OAuth rollback answer for support",
            "description": "Give support a customer-facing answer if sign-in is rolled back.",
            "status": "open",
            "owner": "",
            "priority": "normal",
            "kind": "step",
            "depends_on": [],
            "evidence": ["Support has not been briefed on the OAuth rollback path"],
            "at": now - 1 * day,
        },
    ]


# The recorded reasoning behind the security gate: a policy produced a pipeline
# dependency, which produced the engineering decision to hold the deploy. These
# are the edges get_reasoning_chain walks.
RELATIONSHIPS = [
    (
        "External auth changes require a security review",
        "Production deployment requires a completed security approval",
        "SUPPORTS",
    ),
    (
        "Production deployment requires a completed security approval",
        "Production deploy waits for the security sign-off",
        "SUPPORTS",
    ),
    (
        "Production deploy waits for the security sign-off",
        "OAuth security review is still open in the security tracker",
        "SUPPORTS",
    ),
    (
        "OAuth security review approved for Friday release",
        "OAuth security review is still open in the security tracker",
        "CONTRADICTS",
    ),
    (
        "Checkout OAuth sign-in launches Friday 09:00 UTC",
        "Launch checklist for checkout OAuth",
        "SUPPORTS",
    ),
]


def seed_launch_scenario(
    workspace_id: str,
    create_project: Callable[[str], str],
    company_memory: Any,
) -> dict:
    """Create (or reuse) the multi-space launch scenario for this workspace."""
    now = datetime.now(timezone.utc)
    space_ids: dict[str, str] = {}
    existing = {
        record["name"]: record["id"]
        for record in rows(
            "SELECT p.id,p.name FROM projects p "
            "JOIN workspace_projects wp ON wp.project_id=p.id WHERE wp.workspace_id=?",
            (workspace_id,),
        )
    }
    for name, _ in SPACES:
        if name in existing:
            space_ids[name] = existing[name]
            continue
        project_id = create_project(name)
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO workspace_projects VALUES (?,?)",
                (workspace_id, project_id),
            )
        space_ids[name] = project_id

    memory_ids: dict[str, str] = {}
    created_memories = 0
    for entry in _memory_plan(now):
        project_id = space_ids[entry["space"]]
        found = row(
            "SELECT id FROM memory_units WHERE project_id=? AND lower(subject)=lower(?) "
            "AND is_latest=1 LIMIT 1",
            (project_id, entry["subject"]),
        )
        if found:
            memory_ids[entry["subject"]] = found["id"]
            continue
        source_type, source_title = entry["source"]
        source_id = new_id("src")
        stamp = _iso(entry["at"])
        with connect() as conn:
            conn.execute(
                "INSERT INTO knowledge_items "
                "(id,project_id,source_type,source_id,source_title,source_url,content,"
                "metadata_json,created_at) VALUES (?,?,?,?,?,'',?,'{}',?)",
                (
                    new_id("item"),
                    project_id,
                    source_type,
                    source_id,
                    source_title,
                    entry["content"],
                    stamp,
                ),
            )
        unit = company_memory.create(
            project_id,
            entry["type"],
            entry["subject"],
            entry["content"],
            [source_id],
            0.94,
            {"service": "checkout"},
        )
        memory_id = unit.get("id", "")
        if memory_id:
            # Backdate to the moment the organization actually learned this, so
            # "what changed this week" and "which record is newer" mean something.
            with connect() as conn:
                conn.execute(
                    "UPDATE memory_units SET created_at=?,updated_at=?,valid_from=? WHERE id=?",
                    (stamp, stamp, stamp, memory_id),
                )
            memory_ids[entry["subject"]] = memory_id
            created_memories += 1

    # Fill in ids for memories that already existed on a previous run.
    for entry in _memory_plan(now):
        if entry["subject"] not in memory_ids:
            found = row(
                "SELECT id FROM memory_units WHERE project_id=? AND lower(subject)=lower(?) "
                "AND is_latest=1 LIMIT 1",
                (space_ids[entry["space"]], entry["subject"]),
            )
            if found:
                memory_ids[entry["subject"]] = found["id"]

    for source_subject, target_subject, relationship in RELATIONSHIPS:
        source_id = memory_ids.get(source_subject)
        target_id = memory_ids.get(target_subject)
        if not source_id or not target_id:
            continue
        source_project = row("SELECT project_id FROM memory_units WHERE id=?", (source_id,))
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO memory_relationships VALUES (?,?,?,?,?,?)",
                (
                    new_id("rel"),
                    (source_project or {}).get("project_id", ""),
                    source_id,
                    target_id,
                    relationship,
                    utcnow(),
                ),
            )

    task_ids: dict[str, str] = {}
    created_tasks = 0
    plan = _task_plan(now)
    for entry in plan:
        project_id = space_ids[entry["space"]]
        found = row(
            "SELECT id FROM org_tasks WHERE project_id=? AND external_key=?",
            (project_id, entry["key"]),
        )
        if found:
            task_ids[entry["key"]] = found["id"]
            continue
        task_id = new_id("task")
        stamp = _iso(entry["at"])
        with connect() as conn:
            conn.execute(
                "INSERT INTO org_tasks (id,workspace_id,project_id,title,description,status,"
                "owner,priority,kind,source_memory_ids_json,depends_on_json,external_key,"
                "created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,'[]',?,?,?)",
                (
                    task_id,
                    workspace_id,
                    project_id,
                    entry["title"],
                    entry["description"],
                    entry["status"],
                    entry["owner"],
                    entry["priority"],
                    entry["kind"],
                    json.dumps(
                        [memory_ids[subject] for subject in entry["evidence"] if subject in memory_ids]
                    ),
                    entry["key"],
                    stamp,
                    stamp,
                ),
            )
        task_ids[entry["key"]] = task_id
        created_tasks += 1

    # Dependencies are written in a second pass: a task can depend on one that is
    # created after it, and a forward reference would otherwise be dropped.
    for entry in plan:
        task_id = task_ids.get(entry["key"])
        if not task_id or not entry["depends_on"]:
            continue
        resolved = [task_ids[key] for key in entry["depends_on"] if key in task_ids]
        with connect() as conn:
            conn.execute(
                "UPDATE org_tasks SET depends_on_json=? WHERE id=?",
                (json.dumps(resolved), task_id),
            )

    return {
        "workspace_id": workspace_id,
        "space_ids": space_ids,
        "memory_ids": memory_ids,
        "task_ids": task_ids,
        "created_memories": created_memories,
        "created_tasks": created_tasks,
        "launch_task_id": task_ids.get("launch_goal", ""),
        "security_task_id": task_ids.get("security_approval", ""),
    }


def reset_launch_scenario(workspace_id: str) -> dict:
    """Put the scenario back to its "not ready" state so the demo can run again.

    Approving the reconcile plan really does change stored state — that is the
    point of the gate — so replaying the walkthrough needs an explicit way to
    rewind it rather than a second copy of the organization.
    """
    now = datetime.now(timezone.utc)
    space_ids = {
        record["name"]: record["id"]
        for record in rows(
            "SELECT p.id,p.name FROM projects p "
            "JOIN workspace_projects wp ON wp.project_id=p.id WHERE wp.workspace_id=?",
            (workspace_id,),
        )
    }
    restored = 0
    for entry in _task_plan(now):
        project_id = space_ids.get(entry["space"])
        if not project_id:
            continue
        stamp = _iso(entry["at"])
        with connect() as conn:
            cursor = conn.execute(
                "UPDATE org_tasks SET status=?,owner=?,priority=?,updated_at=? "
                "WHERE project_id=? AND external_key=?",
                (
                    entry["status"],
                    entry["owner"],
                    entry["priority"],
                    stamp,
                    project_id,
                    entry["key"],
                ),
            )
            restored += cursor.rowcount
    with connect() as conn:
        conn.execute("DELETE FROM org_action_plans WHERE workspace_id=?", (workspace_id,))
    return {"restored_tasks": restored}
