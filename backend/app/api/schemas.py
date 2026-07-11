from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class GitHubIngestRequest(BaseModel):
    repo_url_or_path: str
    project_name: str
    workspace_id: str | None = None


class UploadRequest(BaseModel):
    project_id: str
    source_type: Literal[
        "incident",
        "slack_export",
        "gmail_export",
        "clickup_ticket",
        "github_issue_export",
        "log",
        "doc",
        "support_ticket",
        "other",
        "slack",
    ]
    title: str
    content: str
    source_url: str = ""


class SlackIngestRequest(BaseModel):
    project_id: str
    channel_id: str
    limit: int = Field(200, ge=1, le=1000)


class TokenRequest(BaseModel):
    token: str
    display_name: str = "Local connection"


class AskRequest(BaseModel):
    project_id: str
    query: str


class ExtractRequest(BaseModel):
    project_id: str
    query: str
    scope: Literal["repo", "service", "incident", "workflow", "all"] = "all"
    service_name: str | None = None


class ProposeRequest(BaseModel):
    project_id: str
    runbook_id: str
    action_id: str
    params: dict[str, Any] = Field(default_factory=dict)


class ResolveRequest(BaseModel):
    action_id: str
    resolved_by: str = "demo-user"


class DevLoginRequest(BaseModel):
    email: str = "demo@runbook.local"
    display_name: str = "Demo User"


class WorkspaceCreateRequest(BaseModel):
    name: str


class InviteMemberRequest(BaseModel):
    email: str
    role: Literal["owner", "admin", "member", "viewer"] = "member"


class SimulateRequest(BaseModel):
    project_id: str
    runbook_id: str | None = None
    scenario: str = ""
    environment: str = "production"
    params: dict[str, Any] = Field(default_factory=dict)


class CorrelateRequest(BaseModel):
    project_id: str
    query: str = ""
    service_name: str | None = None


class MemoryResolveRequest(BaseModel):
    resolved_by: str = "demo-user"


class ApiKeyCreateRequest(BaseModel):
    name: str
    workspace_id: str = ""


class ImporterRunRequest(BaseModel):
    project_id: str
    resource: Literal[
        "incidents", "services", "escalation_policies", "postmortems", "status_updates"
    ] = "incidents"
    limit: int = Field(50, ge=1, le=200)


class ChangeImpactAnalyzeRequest(BaseModel):
    type: Literal["github_pull_request", "commit", "repository_reingestion", "manual"] = "manual"
    ref: str = ""
    changed_files: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    environment_variables: list[str] = Field(default_factory=list)
    config_keys: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    workflows: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AssertionDecisionRequest(BaseModel):
    actor: str = "demo-user"
    reason: str = ""
    superseded_by: str = ""
