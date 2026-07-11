from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse

from app.approvals import ApprovalService
from app.audit import AuditService
from app.auth import ConnectorSecrets, OAuthStateStore
from app.auth.api_keys import create_api_key, list_api_keys, revoke_api_key
from app.auth.app_auth import (
    bearer_token,
    create_dev_session,
    create_workspace,
    invite_member,
    list_workspaces,
    logout,
    me_from_token,
    workspace_members,
)
from app.connectors.github import GitHubConnector
from app.connectors.slack import SlackConnector
from app.connectors.stubs import planned_connectors
from app.core.config import settings
from app.core.database import connect, decode, new_id, row, rows, utcnow
from app.graph import get_graph_store
from app.hcag_adapter import HCAGAdapter
from app.importers import NotConnectedError, get_importer, importer_statuses
from app.ingestion.repository import RepositoryIngestor
from app.ingestion.service import IngestionService
from app.ingestion.slack import SlackIngestor
from app.intelligence import DriftService, SimulationService, blast_radius, correlate_changes
from app.memory import OperationalMemoryService
from app.reliability import ChangeImpactService, OperationalAssertionService
from app.retrieval import RetrievalService
from app.runbooks import RunbookService

from .schemas import (
    ApiKeyCreateRequest,
    AskRequest,
    AssertionDecisionRequest,
    ChangeImpactAnalyzeRequest,
    CorrelateRequest,
    DevLoginRequest,
    ExtractRequest,
    GitHubIngestRequest,
    ImporterRunRequest,
    InviteMemberRequest,
    MemoryResolveRequest,
    ProposeRequest,
    ResolveRequest,
    SimulateRequest,
    SlackIngestRequest,
    TokenRequest,
    UploadRequest,
    WorkspaceCreateRequest,
)

router = APIRouter(prefix="/api")
graph = get_graph_store()
audit = AuditService()
hcag = HCAGAdapter(graph)
ingestion = IngestionService(graph, hcag, audit)
github = GitHubConnector()
slack = SlackConnector()
repository_ingestor = RepositoryIngestor(ingestion, graph, github)
slack_ingestor = SlackIngestor(ingestion, graph, slack)
retrieval = RetrievalService(hcag, audit)
runbooks = RunbookService(graph, hcag, audit)
approvals = ApprovalService(graph, runbooks, audit=audit)
drift = DriftService(graph, runbooks, hcag, audit)
simulation = SimulationService(runbooks, approvals.gate, audit)
memories = OperationalMemoryService(graph, audit)
assertions = OperationalAssertionService(graph, audit)
change_impacts = ChangeImpactService(graph, assertions, audit)


def fail(exc: Exception):
    raise HTTPException(status_code=400, detail=str(exc)) from exc


def _authorize_project(project_id: str, authorization: str | None, write: bool = False) -> dict:
    """Authorize reliability data through the caller's active workspace."""
    principal = me_from_token(bearer_token(authorization))
    if not principal and settings.auth_dev_mode:
        principal = create_dev_session()["user"]
    if not principal:
        raise HTTPException(401, "Not authenticated")
    if write and principal["role"] == "viewer":
        raise HTTPException(403, "Viewer role cannot make reliability decisions")
    if not row("SELECT id FROM projects WHERE id=?", (project_id,)):
        raise HTTPException(404, "Project not found")
    linked = rows("SELECT workspace_id FROM workspace_projects WHERE project_id=?", (project_id,))
    workspace_id = principal.get("active_workspace_id", "")
    if linked and workspace_id not in {item["workspace_id"] for item in linked}:
        raise HTTPException(403, "Project is not in the active workspace")
    if not linked:
        if principal["role"] not in {"owner", "admin"}:
            raise HTTPException(403, "Only an owner or admin can claim an unlinked project")
        with connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO workspace_projects VALUES (?,?)", (workspace_id, project_id)
            )
    return principal


@router.get("/health")
def health():
    return {"status": "ok", "product": "Runbook"}


@router.get("/auth/me")
def auth_me(authorization: str | None = Header(default=None)):
    token = bearer_token(authorization)
    principal = me_from_token(token)
    if principal:
        return principal
    if settings.auth_dev_mode:
        return create_dev_session()["user"]
    raise HTTPException(401, "Not authenticated")


@router.post("/auth/dev-login")
def auth_dev_login(request: DevLoginRequest):
    try:
        return create_dev_session(request.email, request.display_name)
    except Exception as exc:
        fail(exc)


@router.post("/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)):
    return logout(bearer_token(authorization))


@router.get("/workspaces")
def workspaces(authorization: str | None = Header(default=None)):
    return list_workspaces(bearer_token(authorization))


@router.post("/workspaces")
def create_workspace_endpoint(
    request: WorkspaceCreateRequest, authorization: str | None = Header(default=None)
):
    try:
        return create_workspace(request.name, bearer_token(authorization))
    except Exception as exc:
        fail(exc)


@router.get("/workspaces/{workspace_id}/members")
def members(workspace_id: str):
    return workspace_members(workspace_id)


@router.post("/workspaces/{workspace_id}/members/invite")
def invite(workspace_id: str, request: InviteMemberRequest):
    try:
        return invite_member(workspace_id, request.email, request.role)
    except Exception as exc:
        fail(exc)


@router.get("/health/graph")
def graph_health():
    try:
        return graph.health()
    except Exception as exc:
        return {
            "backend": "arcadedb",
            "connected": False,
            "database": settings.arcadedb_database,
            "error": str(exc),
        }


@router.get("/projects/{project_id}/graph/summary")
def project_graph_summary(project_id: str):
    try:
        return graph.graph_summary(project_id)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/graph/nodes")
def project_graph_nodes(
    project_id: str, node_type: str | None = None, limit: int = Query(200, ge=1, le=1000)
):
    try:
        return graph.list_nodes(project_id, node_type, limit)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/graph/edges")
def project_graph_edges(
    project_id: str, edge_type: str | None = None, limit: int = Query(200, ge=1, le=1000)
):
    try:
        return graph.list_edges(project_id, edge_type, limit)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/graph/service/{service_name}")
def project_service_graph(project_id: str, service_name: str):
    try:
        return graph.service_graph(project_id, service_name)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/graph/file")
def project_file_graph(project_id: str, path: str):
    try:
        return graph.file_graph(project_id, path)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/graph/trace")
def project_graph_trace(project_id: str, chunk_ids: str = ""):
    try:
        return graph.get_retrieval_trace(
            project_id, [value for value in chunk_ids.split(",") if value]
        )
    except Exception as exc:
        fail(exc)


@router.get("/overview")
def overview():
    counts = {
        "projects": row("SELECT COUNT(*) value FROM projects")["value"],
        "knowledge_items": row("SELECT COUNT(*) value FROM knowledge_items")["value"],
        "runbooks": row("SELECT COUNT(*) value FROM runbooks")["value"],
        "pending_approvals": row("SELECT COUNT(*) value FROM actions WHERE status='pending'")[
            "value"
        ],
        "recent_queries": row(
            "SELECT COUNT(*) value FROM audit_events WHERE event_type='query.answered'"
        )["value"],
        "connected_sources": row(
            "SELECT COUNT(*) value FROM connector_accounts WHERE status='connected'"
        )["value"],
    }
    return {**counts, "graph": graph_health(), "recent_activity": audit.list(limit=8)}


@router.get("/settings/runtime")
def runtime_settings():
    return {
        "environment": settings.environment,
        "auth_dev_mode": settings.auth_dev_mode,
        "runbook_demo_mode": settings.runbook_demo_mode,
        "allow_local_command_execution": settings.allow_local_command_execution,
        "graph_backend": settings.graph_backend,
        "arcadedb_database": settings.arcadedb_database,
        "hcag_enabled": True,
        "agentgate_enabled": True,
        "github_oauth_configured": bool(
            settings.github_client_id and settings.github_client_secret
        ),
        "slack_oauth_configured": bool(settings.slack_client_id and settings.slack_client_secret),
    }


@router.get("/projects")
def list_projects():
    return rows(
        "SELECT p.*, (SELECT COUNT(*) FROM knowledge_items k WHERE k.project_id=p.id) knowledge_items, (SELECT COUNT(*) FROM runbooks r WHERE r.project_id=p.id) runbooks FROM projects p ORDER BY created_at DESC"
    )


@router.post("/ingest/github")
def ingest_github(request: GitHubIngestRequest):
    job_id = _create_job(
        source="github",
        source_ref=request.repo_url_or_path,
        workspace_id=request.workspace_id,
    )
    try:
        result = repository_ingestor.ingest(request.repo_url_or_path, request.project_name)
        if result.get("change", {}).get("changed_files"):
            result["change_impact"] = change_impacts.analyze(result["project_id"], result["change"])
        _finish_job(job_id, "succeeded", result)
        return {"job_id": job_id, **result}
    except Exception as exc:
        _fail_job(job_id, exc)
        fail(exc)


@router.post("/ingest/upload")
def ingest_upload(request: UploadRequest):
    job_id = _create_job("upload", request.title, project_id=request.project_id)
    try:
        result = ingestion.ingest_item(
            request.project_id,
            request.source_type,
            request.title,
            request.content,
            request.source_url,
        )
        payload = {"project_id": request.project_id, **result, "status": "success"}
        _finish_job(job_id, "succeeded", payload)
        return {"job_id": job_id, **payload}
    except Exception as exc:
        _fail_job(job_id, exc)
        fail(exc)


@router.post("/ingest/file")
async def ingest_file(
    project_id: str = Form(...), source_type: str = Form("doc"), file: UploadFile = File(...)
):
    suffix = Path(file.filename or "upload.txt").suffix.lower()
    if suffix not in {".md", ".txt", ".json", ".csv", ".log", ".yaml", ".yml"}:
        raise HTTPException(415, "Unsupported file type")
    content = (await file.read()).decode("utf-8", errors="replace")
    return ingestion.ingest_item(project_id, source_type, file.filename or "Upload", content)


@router.post("/ingest/slack")
def ingest_slack(request: SlackIngestRequest):
    job_id = _create_job("slack", request.channel_id, project_id=request.project_id)
    try:
        result = slack_ingestor.ingest_channel(
            request.project_id, request.channel_id, request.limit
        )
        _finish_job(job_id, "succeeded", result)
        return {"job_id": job_id, **result}
    except Exception as exc:
        _fail_job(job_id, exc)
        fail(exc)


@router.get("/ingest/jobs")
def ingest_jobs(project_id: str | None = None):
    if project_id:
        return [
            decode(item)
            for item in rows(
                "SELECT * FROM ingestion_jobs WHERE project_id=? ORDER BY created_at DESC",
                (project_id,),
            )
        ]
    return [
        decode(item)
        for item in rows("SELECT * FROM ingestion_jobs ORDER BY created_at DESC LIMIT 200")
    ]


@router.get("/ingest/jobs/{job_id}")
def ingest_job(job_id: str):
    item = row("SELECT * FROM ingestion_jobs WHERE id=?", (job_id,))
    if not item:
        raise HTTPException(404, "Ingestion job not found")
    return decode(item)


@router.post("/ask")
def ask(request: AskRequest):
    return retrieval.ask(request.project_id, request.query)


@router.post("/runbooks/extract")
def extract_runbooks(request: ExtractRequest):
    return runbooks.extract(request.project_id, request.query)


@router.get("/runbooks")
def list_runbooks(project_id: str | None = None):
    return runbooks.list(project_id)


@router.get("/runbooks/{runbook_id}")
def get_runbook(runbook_id: str, project_id: str | None = None):
    result = runbooks.get(runbook_id, project_id)
    if not result:
        raise HTTPException(404, "Runbook not found")
    return result


@router.get("/projects/{project_id}/change-impacts")
def list_change_impacts(project_id: str, authorization: str | None = Header(default=None)):
    _authorize_project(project_id, authorization)
    return change_impacts.list(project_id)


@router.get("/change-impacts/{impact_id}")
def get_change_impact(impact_id: str, authorization: str | None = Header(default=None)):
    result = change_impacts.get(impact_id)
    if not result:
        raise HTTPException(404, "Change impact not found")
    _authorize_project(result["project_id"], authorization)
    return result


@router.post("/projects/{project_id}/change-impacts/analyze")
def analyze_change_impact(
    project_id: str,
    request: ChangeImpactAnalyzeRequest,
    authorization: str | None = Header(default=None),
):
    _authorize_project(project_id, authorization, write=True)
    try:
        return change_impacts.analyze(project_id, request.model_dump())
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/assertions")
def list_assertions(
    project_id: str, status: str | None = None, authorization: str | None = Header(default=None)
):
    _authorize_project(project_id, authorization)
    return assertions.list(project_id, status)


@router.get("/assertions/{assertion_id}")
def get_assertion(assertion_id: str, authorization: str | None = Header(default=None)):
    result = assertions.get(assertion_id)
    if not result:
        raise HTTPException(404, "Assertion not found")
    _authorize_project(result["project_id"], authorization)
    return result


def _assertion_decision(
    assertion_id: str, action: str, request: AssertionDecisionRequest, authorization: str | None
):
    assertion = assertions.get(assertion_id)
    if not assertion:
        raise HTTPException(404, "Assertion not found")
    _authorize_project(assertion["project_id"], authorization, write=True)
    try:
        return assertions.transition(
            assertion_id,
            action,
            request.actor,
            request.reason,
            assertion["project_id"],
            request.superseded_by,
        )
    except Exception as exc:
        fail(exc)


@router.post("/assertions/{assertion_id}/verify")
def verify_assertion(
    assertion_id: str,
    request: AssertionDecisionRequest,
    authorization: str | None = Header(default=None),
):
    return _assertion_decision(assertion_id, "verify", request, authorization)


@router.post("/assertions/{assertion_id}/mark-stale")
def stale_assertion(
    assertion_id: str,
    request: AssertionDecisionRequest,
    authorization: str | None = Header(default=None),
):
    return _assertion_decision(assertion_id, "mark_stale", request, authorization)


@router.post("/assertions/{assertion_id}/supersede")
def supersede_assertion(
    assertion_id: str,
    request: AssertionDecisionRequest,
    authorization: str | None = Header(default=None),
):
    return _assertion_decision(assertion_id, "supersede", request, authorization)


@router.post("/assertions/{assertion_id}/dismiss")
def dismiss_assertion(
    assertion_id: str,
    request: AssertionDecisionRequest,
    authorization: str | None = Header(default=None),
):
    return _assertion_decision(assertion_id, "dismiss", request, authorization)


@router.post("/actions/propose")
def propose_action(request: ProposeRequest):
    try:
        return approvals.propose(
            request.project_id, request.runbook_id, request.action_id, request.params
        )
    except Exception as exc:
        fail(exc)


@router.post("/actions/approve")
def approve_action(request: ResolveRequest):
    try:
        return approvals.resolve(request.action_id, True, request.resolved_by)
    except Exception as exc:
        fail(exc)


@router.post("/actions/deny")
def deny_action(request: ResolveRequest):
    try:
        return approvals.resolve(request.action_id, False, request.resolved_by)
    except Exception as exc:
        fail(exc)


@router.get("/actions/pending")
def pending_actions(project_id: str | None = None):
    return approvals.list("pending", project_id)


@router.get("/actions")
def all_actions(project_id: str | None = None):
    return approvals.list(None, project_id)


@router.get("/audit/actions")
def action_audit(project_id: str | None = None):
    return approvals.list(None, project_id)


@router.get("/audit")
def audit_log(project_id: str | None = None, limit: int = Query(200, ge=1, le=1000)):
    return audit.list(project_id, limit)


@router.get("/projects/{project_id}/graph/blast-radius/{service_name}")
def project_blast_radius(project_id: str, service_name: str):
    try:
        return blast_radius(graph, project_id, service_name)
    except Exception as exc:
        fail(exc)


@router.post("/simulate")
def simulate(request: SimulateRequest):
    try:
        return simulation.simulate(
            request.project_id,
            request.runbook_id,
            request.scenario,
            request.environment,
            request.params,
        )
    except Exception as exc:
        fail(exc)


@router.post("/correlate")
def correlate(request: CorrelateRequest):
    try:
        route = hcag.route_query(request.project_id, request.query or request.service_name or "")
        evidence = hcag.retrieve_context(
            request.project_id,
            request.query or f"{request.service_name} failure",
            request.service_name or route.service_name,
        )
        return correlate_changes(
            request.project_id, evidence, request.service_name or route.service_name
        )
    except Exception as exc:
        fail(exc)


@router.get("/runbooks/{runbook_id}/drift")
def runbook_drift(runbook_id: str, project_id: str | None = None):
    try:
        return drift.check_runbook(runbook_id, project_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/drift")
def project_drift(project_id: str):
    try:
        return drift.check_project(project_id)
    except Exception as exc:
        fail(exc)


@router.get("/projects/{project_id}/memories")
def list_memories(project_id: str, status: str | None = None):
    return memories.list(project_id, status)


@router.post("/projects/{project_id}/memories/derive")
def derive_memories(project_id: str):
    try:
        return memories.derive(project_id)
    except Exception as exc:
        fail(exc)


@router.post("/memories/{memory_id}/approve")
def approve_memory(memory_id: str, request: MemoryResolveRequest):
    try:
        return memories.resolve(memory_id, True, request.resolved_by)
    except Exception as exc:
        fail(exc)


@router.post("/memories/{memory_id}/reject")
def reject_memory(memory_id: str, request: MemoryResolveRequest):
    try:
        return memories.resolve(memory_id, False, request.resolved_by)
    except Exception as exc:
        fail(exc)


@router.get("/importers")
def importers():
    return importer_statuses()


@router.post("/importers/{name}/import")
def run_importer(name: str, request: ImporterRunRequest):
    try:
        importer = get_importer(name)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    try:
        method = getattr(importer, f"import_{request.resource}")
        if request.resource == "incidents":
            result = method(ingestion, request.project_id, request.limit)
        else:
            result = method(ingestion, request.project_id)
        audit.record(
            "importer.ran",
            f"Imported {request.resource} from {importer.label}",
            request.project_id,
            payload=result,
        )
        return result
    except NotConnectedError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        fail(exc)


@router.get("/keys")
def api_keys(workspace_id: str = ""):
    return list_api_keys(workspace_id)


@router.post("/keys")
def create_key(request: ApiKeyCreateRequest):
    try:
        result = create_api_key(request.name, request.workspace_id)
        audit.record("api_key.created", f"Created API key {request.name}")
        return result
    except Exception as exc:
        fail(exc)


@router.delete("/keys/{key_id}")
def revoke_key(key_id: str):
    try:
        result = revoke_api_key(key_id)
        audit.record("api_key.revoked", f"Revoked API key {key_id}")
        return result
    except Exception as exc:
        fail(exc)


@router.get("/benchmarks")
def benchmark_reports():
    """Serve the latest HCAG benchmark report if one has been generated.

    Reports are only ever produced by running `make benchmark` in the hcag
    project; this endpoint never fabricates metrics.
    """
    candidates = [
        settings.hcag_path / "benchmark_reports" / "latest.json",
        settings.local_repo_mount / "hcag" / "benchmark_reports" / "latest.json",
    ]
    for path in candidates:
        try:
            if path.exists():
                return {
                    "available": True,
                    "path": str(path),
                    "report": json.loads(path.read_text()),
                }
        except Exception:
            continue
    return {
        "available": False,
        "report": None,
        "reason": "No benchmark report found. Run `make benchmark` in the hcag project to generate one.",
    }


@router.get("/connectors")
def connectors():
    return [github.status().__dict__, slack.status().__dict__, *planned_connectors()]


@router.get("/connectors/github/status")
def github_status():
    return github.status().__dict__


@router.post("/connectors/github/token")
def github_token(request: TokenRequest):
    try:
        GitHubConnector()._api("GET", "/user", token=request.token)
        user = GitHubConnector()._api("GET", "/user", token=request.token)
        ConnectorSecrets().save("github", str(user["id"]), user["login"], request.token)
        audit.record(
            "connector.connected",
            f"Connected GitHub as {user['login']}",
            payload={"provider": "github"},
        )
        return {"connected": True, "display_name": user["login"]}
    except Exception as exc:
        fail(exc)


@router.get("/connectors/github/repos")
def github_repos():
    try:
        return github.list_repositories()
    except Exception as exc:
        fail(exc)


@router.get("/auth/github/start")
def github_auth_start():
    try:
        return RedirectResponse(github.oauth_url(OAuthStateStore()))
    except Exception as exc:
        fail(exc)


@router.get("/connectors/github/auth/start")
def github_connector_auth_start():
    return github_auth_start()


@router.get("/auth/github/callback")
def github_auth_callback(code: str, state: str):
    try:
        github.complete_oauth(code, state, OAuthStateStore())
        return RedirectResponse(f"{settings.frontend_url}/connectors?connected=github")
    except Exception as exc:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error={str(exc)}")


@router.get("/connectors/github/auth/callback")
def github_connector_auth_callback(code: str, state: str):
    return github_auth_callback(code, state)


@router.get("/connectors/slack/status")
def slack_status():
    return slack.status().__dict__


@router.post("/connectors/slack/token")
def slack_token(request: TokenRequest):
    try:
        data = (
            SlackConnector()._api("auth.test", {})
            if request.token == slack.token()
            else _verify_slack(request.token)
        )
        ConnectorSecrets().save(
            "slack",
            data.get("team_id", "local"),
            data.get("team", request.display_name),
            request.token,
        )
        audit.record(
            "connector.connected",
            f"Connected Slack workspace {data.get('team', '')}",
            payload={"provider": "slack"},
        )
        return {"connected": True, "display_name": data.get("team", request.display_name)}
    except Exception as exc:
        fail(exc)


def _verify_slack(token: str):
    import httpx

    response = httpx.post(
        "https://slack.com/api/auth.test", headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise ValueError(f"Slack token rejected: {payload.get('error')}")
    return payload


@router.get("/connectors/slack/channels")
def slack_channels():
    try:
        return slack.list_channels()
    except Exception as exc:
        fail(exc)


@router.get("/auth/slack/start")
def slack_auth_start():
    try:
        return RedirectResponse(slack.oauth_url(OAuthStateStore()))
    except Exception as exc:
        fail(exc)


@router.get("/connectors/slack/auth/start")
def slack_connector_auth_start():
    return slack_auth_start()


@router.get("/auth/slack/callback")
def slack_auth_callback(code: str, state: str):
    try:
        slack.complete_oauth(code, state, OAuthStateStore())
        return RedirectResponse(f"{settings.frontend_url}/connectors?connected=slack")
    except Exception as exc:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error={str(exc)}")


@router.get("/connectors/slack/auth/callback")
def slack_connector_auth_callback(code: str, state: str):
    return slack_auth_callback(code, state)


def _create_job(
    source: str,
    source_ref: str,
    project_id: str | None = None,
    workspace_id: str | None = None,
) -> str:
    job_id = new_id("job")
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO ingestion_jobs
            (id, project_id, workspace_id, source, source_ref, status, progress,
             warnings_json, created_at, updated_at)
            VALUES (?,?,?,?,?,'running',5,'[]',?,?)
            """,
            (job_id, project_id, workspace_id, source, source_ref, now, now),
        )
    audit.record(
        "ingestion.job_started",
        f"Started {source} ingestion",
        project_id,
        payload={"job_id": job_id, "source_ref": source_ref},
    )
    return job_id


def _finish_job(job_id: str, status: str, result: dict) -> None:
    now = utcnow()
    project_id = result.get("project_id")
    with connect() as conn:
        conn.execute(
            """
            UPDATE ingestion_jobs SET
              project_id=COALESCE(?, project_id), status=?, progress=100,
              files_scanned=?, issues_scanned=?, pull_requests_scanned=?,
              knowledge_items_created=?, knowledge_chunks_created=?,
              graph_nodes_created=?, graph_edges_created=?, warnings_json=?,
              updated_at=?, completed_at=?
            WHERE id=?
            """,
            (
                project_id,
                status,
                int(result.get("files_scanned", 0) or 0),
                int(result.get("issues_scanned", 0) or 0),
                int(result.get("pull_requests_scanned", 0) or 0),
                int(result.get("knowledge_items_created", 1 if result.get("item_id") else 0) or 0),
                int(result.get("knowledge_chunks_created", result.get("chunks_created", 0)) or 0),
                int(result.get("graph_nodes_created", 0) or 0),
                int(result.get("graph_edges_created", 0) or 0),
                json.dumps(result.get("warnings", [])),
                now,
                now,
                job_id,
            ),
        )
        job = conn.execute(
            "SELECT workspace_id FROM ingestion_jobs WHERE id=?", (job_id,)
        ).fetchone()
        if job and job["workspace_id"] and project_id:
            conn.execute(
                "INSERT OR IGNORE INTO workspace_projects VALUES (?,?)",
                (job["workspace_id"], project_id),
            )
    audit.record(
        "ingestion.job_finished",
        f"Finished ingestion job {job_id}",
        project_id,
        payload={"job_id": job_id, "status": status},
    )


def _fail_job(job_id: str, exc: Exception) -> None:
    now = utcnow()
    with connect() as conn:
        conn.execute(
            """
            UPDATE ingestion_jobs SET status='failed', progress=100, error=?,
              updated_at=?, completed_at=? WHERE id=?
            """,
            (str(exc), now, now, job_id),
        )
    audit.record(
        "ingestion.job_failed",
        f"Ingestion job {job_id} failed",
        payload={"job_id": job_id, "error": str(exc)},
    )
