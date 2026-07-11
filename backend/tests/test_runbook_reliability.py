"""Reliability workflow tests use the same graph and state services as the API."""

import pytest

from app.approvals import ApprovalService
from app.audit import AuditService
from app.auth.app_auth import create_dev_session, create_workspace
from app.core.database import connect
from app.graph.migrations import EDGE_TYPES, VERTEX_TYPES
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.reliability import ChangeImpactService, OperationalAssertionService
from app.runbooks import RunbookService


def _services(graph):
    audit = AuditService()
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, audit)
    runbooks = RunbookService(graph, hcag, audit)
    assertions = OperationalAssertionService(graph, audit)
    impacts = ChangeImpactService(graph, assertions, audit)
    return audit, ingestion, runbooks, assertions, impacts


def _runbook(project_id: str, runbooks: RunbookService) -> dict:
    return runbooks.save(
        project_id,
        {
            "id": "restart_api",
            "name": "Restart API",
            "description": "Evidence-backed API recovery",
            "risk_level": "high",
            "confidence": 0.8,
            "services": ["api_service"],
            "triggers": ["api failure"],
            "sources": [],
            "steps": [
                {
                    "id": "step_1",
                    "description": "Restart api_service with docker restart api_service.",
                    "action_type": "mutation",
                    "approval_required": True,
                    "command_template": "docker restart api_service",
                }
            ],
            "approval_rules": [],
            "graph_trace": [],
            "trust_score": {"score": 0.8},
        },
    )


def test_assertion_is_graph_backed_and_project_scoped(graph):
    _, ingestion, runbooks, assertions, _ = _services(graph)
    project_id = ingestion.create_project("Reliability")
    saved = _runbook(project_id, runbooks)

    records = assertions.list(project_id)
    assert len(records) == 1
    assertion = records[0]
    assert assertion["status"] == "proposed"
    assert assertion["affected_runbook_ids"] == [saved["record_id"]]
    assert graph.vertices["OperationalAssertion"][assertion["id"]]["project_id"] == project_id
    assert any(edge["relationship"] == "ASSERTION_AFFECTS_RUNBOOK_STEP" for edge in graph.edges)
    assert assertions.get(assertion["id"], "prj_other") is None
    assert "OperationalAssertion" in VERTEX_TYPES
    assert "ChangeImpact" in VERTEX_TYPES
    assert "CHANGE_IMPACT_FOR_ASSERTION" in EDGE_TYPES


def test_change_impact_reports_direct_evidence_without_claiming_invalidity(graph):
    _, ingestion, runbooks, assertions, impacts = _services(graph)
    project_id = ingestion.create_project("Impact")
    saved = _runbook(project_id, runbooks)
    file_id = f"file:{project_id}:deploy/config.yaml"
    graph.upsert_file({"id": file_id, "project_id": project_id, "path": "deploy/config.yaml"})
    assertion = assertions.create(
        project_id,
        {
            "title": "API config value",
            "claim": "The API restart procedure uses the deployed config.",
            "subject_type": "file",
            "subject_id": file_id,
            "status": "verified",
            "confidence": 0.9,
            "trust_score": 0.9,
            "affected_runbook_ids": [saved["record_id"]],
            "evidence": [{"source_item_id": "", "snippet": "config", "graph_paths": []}],
        },
    )
    report = impacts.analyze(
        project_id,
        {
            "type": "github_pull_request",
            "ref": "PR #42",
            "changed_files": ["deploy/config.yaml"],
            "evidence": [
                {"kind": "github_pr", "detail": "Changed deploy/config.yaml", "commit_sha": "abc"}
            ],
        },
    )
    item = next(item for item in report["impacts"] if item["assertion_id"] == assertion["id"])
    assert item["connection"] == "direct_graph_edge"
    assert item["inference"] is False
    assert item["status"] == "possibly_stale"
    assert "not proof" in report["evidence_limit"]
    assert assertions.get(assertion["id"], project_id)["status"] == "possibly_stale"


def test_indirect_change_impact_is_explicitly_inference(graph):
    _, ingestion, runbooks, assertions, impacts = _services(graph)
    project_id = ingestion.create_project("Indirect impact")
    saved = _runbook(project_id, runbooks)
    assertion = assertions.create(
        project_id,
        {
            "title": "API service procedure",
            "claim": "Restarting the API is applicable.",
            "subject_type": "runbook_step",
            "subject_id": f"{saved['record_id']}:step_1",
            "confidence": 0.7,
            "trust_score": 0.7,
            "affected_runbook_ids": [saved["record_id"]],
            "affected_runbook_step_ids": [f"{saved['record_id']}:step_1"],
        },
    )
    report = impacts.analyze(
        project_id, {"type": "commit", "ref": "abc", "services": ["api_service"]}
    )
    item = next(item for item in report["impacts"] if item["assertion_id"] == assertion["id"])
    assert item["connection"] == "runbook_service_overlap"
    assert item["inference"] is True
    assert item["status"] == "possibly_stale"


def test_assertion_lifecycle_is_audited_and_requires_reason(graph):
    audit, ingestion, _, assertions, _ = _services(graph)
    project_id = ingestion.create_project("Lifecycle")
    assertion = assertions.create(
        project_id,
        {
            "title": "Config",
            "claim": "Config is current",
            "subject_type": "config_key",
            "subject_id": "config:x",
        },
    )
    verified = assertions.transition(
        assertion["id"], "verify", "operator", "Checked current deployment", project_id
    )
    assert verified["status"] == "verified"
    stale = assertions.transition(
        assertion["id"], "mark_stale", "operator", "Changed config", project_id
    )
    assert stale["status"] == "stale"
    dismissed = assertions.transition(
        assertion["id"], "dismiss", "operator", "False positive; documented exception", project_id
    )
    assert dismissed["status"] == "stale"
    assert dismissed["policy_status"] == "dismissed"
    events = audit.list(project_id)
    assert {event["event_type"] for event in events} >= {
        "assertion.verify",
        "assertion.mark_stale",
        "assertion.dismiss",
    }


def test_production_proposal_has_unresolved_assertion_reliability_gate(graph):
    audit, ingestion, runbooks, _, _ = _services(graph)
    project_id = ingestion.create_project("Production gate")
    saved = _runbook(project_id, runbooks)
    proposal = ApprovalService(graph, runbooks, audit=audit).propose(
        project_id,
        saved["record_id"],
        "step_1",
        {"environment": "production"},
    )
    assert proposal["approval_required"] is True
    assert proposal["approval_role"] == "admin"
    assert proposal["assertion_policy"]["trusted"] is False
    assert "unresolved" in proposal["reason"].lower()


def test_reliability_workspace_and_project_isolation(graph):
    _, ingestion, _, assertions, impacts = _services(graph)
    project_id = ingestion.create_project("Private reliability")
    assertion = assertions.create(
        project_id,
        {
            "title": "Private claim",
            "claim": "Only this project can read this claim",
            "subject_type": "service",
            "subject_id": f"{project_id}:api",
        },
    )
    owner = create_dev_session("reliability-owner@example.com", "Owner")
    workspace = create_workspace("Reliability private workspace", owner["token"])
    with connect() as conn:
        conn.execute("INSERT INTO workspace_projects VALUES (?,?)", (workspace["id"], project_id))
    other = create_dev_session("reliability-other@example.com", "Other")

    from app.api.routes import _authorize_project

    with pytest.raises(Exception) as exc_info:
        _authorize_project(project_id, f"Bearer {other['token']}")
    assert getattr(exc_info.value, "status_code", None) == 403
    assert assertions.get(assertion["id"], "prj_unrelated") is None
    assert impacts.get("impact_does_not_exist", "prj_unrelated") is None
