from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_name: str = "Runbook"
    environment: str = "development"
    log_level: str = "INFO"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    sqlite_path: Path = ROOT / "data" / "runbook.db"
    generated_runbooks_dir: Path = ROOT / "generated_runbooks"
    repo_cache_dir: Path = ROOT / "data" / "repos"
    local_repo_mount: Path = Path("/workspace/local_repos")

    graph_backend: str = "arcadedb"
    arcadedb_host: str = "localhost"
    arcadedb_port: int = 2480
    arcadedb_user: str = "root"
    arcadedb_password: str = "runbook_dev_password"
    arcadedb_database: str = "runbook"

    hcag_path: Path = ROOT.parent / "hcag"
    agentgate_path: Path = ROOT.parent / "agentgate"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"
    github_token: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/api/auth/slack/callback"
    slack_bot_token: str = ""
    integration_encryption_key: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = ""
    nextauth_secret: str = ""
    jwt_secret: str = "runbook-local-dev-secret"
    app_base_url: str = "http://localhost:3000"
    auth_dev_mode: bool = True

    runbook_demo_mode: bool = False
    allow_local_command_execution: bool = False

    @property
    def arcadedb_url(self) -> str:
        return f"http://{self.arcadedb_host}:{self.arcadedb_port}"


settings = Settings()
