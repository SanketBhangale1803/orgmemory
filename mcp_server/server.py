from __future__ import annotations

import argparse
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

API_URL = os.getenv("RUNBOOK_API_URL", "http://localhost:8000").rstrip("/")
mcp = FastMCP("Runbook")


def call(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    response = httpx.request(method, f"{API_URL}{path}", json=payload, timeout=180)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def runbook_ingest_github_repo(repo_url_or_path: str, project_name: str) -> dict:
    """Ingest an accessible GitHub repository or local repository path."""
    return call("POST", "/api/ingest/github", {"repo_url_or_path": repo_url_or_path, "project_name": project_name})


@mcp.tool()
def runbook_ingest_slack_channel(project_id: str, channel_id: str, limit: int = 200) -> dict:
    """Ingest a connected Slack channel's message history."""
    return call("POST", "/api/ingest/slack", {"project_id": project_id, "channel_id": channel_id, "limit": limit})


@mcp.tool()
def runbook_upload_knowledge(project_id: str, source_type: str, title: str, content: str) -> dict:
    """Ingest pasted operational knowledge through the standard evidence pipeline."""
    return call("POST", "/api/ingest/upload", {"project_id": project_id, "source_type": source_type, "title": title, "content": content})


@mcp.tool()
def runbook_ask(project_id: str, query: str) -> dict:
    """Retrieve evidence and answer with HCAG routing, citations, confidence, and action boundaries."""
    return call("POST", "/api/ask", {"project_id": project_id, "query": query})


@mcp.tool()
def runbook_extract_runbooks(project_id: str, query: str) -> dict:
    """Extract an executable, cited runbook from retrieved evidence."""
    return call("POST", "/api/runbooks/extract", {"project_id": project_id, "query": query})


@mcp.tool()
def runbook_list_runbooks(project_id: str = "") -> list:
    """List generated runbooks, optionally scoped to a project."""
    suffix = f"?project_id={project_id}" if project_id else ""
    return call("GET", f"/api/runbooks{suffix}")


@mcp.tool()
def runbook_get_runbook(runbook_id: str, project_id: str = "") -> dict:
    """Get one runbook including YAML, evidence, steps, and policy rules."""
    suffix = f"?project_id={project_id}" if project_id else ""
    return call("GET", f"/api/runbooks/{runbook_id}{suffix}")


@mcp.tool()
def runbook_propose_action(project_id: str, runbook_id: str, action_id: str, params: dict[str, Any]) -> dict:
    """Evaluate a runbook action through AgentGate and create an approval record."""
    return call("POST", "/api/actions/propose", {"project_id": project_id, "runbook_id": runbook_id, "action_id": action_id, "params": params})


@mcp.tool()
def runbook_list_pending_approvals(project_id: str = "") -> list:
    """List approval requests waiting for human action."""
    suffix = f"?project_id={project_id}" if project_id else ""
    return call("GET", f"/api/actions/pending{suffix}")


@mcp.tool()
def runbook_get_audit_log(project_id: str = "", limit: int = 200) -> list:
    """Read Runbook's audit history."""
    query = f"?limit={limit}" + (f"&project_id={project_id}" if project_id else "")
    return call("GET", f"/api/audit{query}")


@mcp.tool()
def runbook_get_graph_summary(project_id: str) -> dict:
    """Get ArcadeDB node/edge counts, services, and file references for a project."""
    return call("GET", f"/api/projects/{project_id}/graph/summary")


@mcp.tool()
def runbook_get_service_graph(project_id: str, service_name: str) -> dict:
    """Get graph neighbors and evidence for a service."""
    return call("GET", f"/api/projects/{project_id}/graph/service/{service_name}")


@mcp.tool()
def runbook_get_blast_radius(project_id: str, service_name: str) -> dict:
    """Get dependency-based blast radius for a service: dependents, dependencies, env vars, and impact statements derived from real graph edges."""
    return call("GET", f"/api/projects/{project_id}/graph/blast-radius/{service_name}")


@mcp.tool()
def runbook_simulate_incident(project_id: str, scenario: str = "", runbook_id: str = "", environment: str = "production") -> dict:
    """Dry-run a runbook against a scenario: per-step policy decisions, required approvals, dangerous steps, and missing context. Nothing executes."""
    payload: dict[str, Any] = {"project_id": project_id, "scenario": scenario, "environment": environment}
    if runbook_id:
        payload["runbook_id"] = runbook_id
    return call("POST", "/api/simulate", payload)


@mcp.tool()
def runbook_check_runbook_drift(runbook_id: str = "", project_id: str = "") -> dict:
    """Check runbook drift against currently ingested knowledge. Pass runbook_id for one runbook or only project_id for all runbooks in a project."""
    if runbook_id:
        suffix = f"?project_id={project_id}" if project_id else ""
        return call("GET", f"/api/runbooks/{runbook_id}/drift{suffix}")
    if not project_id:
        raise ValueError("Provide runbook_id or project_id")
    return call("GET", f"/api/projects/{project_id}/drift")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runbook MCP stdio server")
    parser.add_argument("--health", action="store_true", help="Check the backend and exit")
    args = parser.parse_args()
    if args.health:
        print(call("GET", "/api/health"))
    else:
        mcp.run(transport="stdio")
