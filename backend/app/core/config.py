from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    app_name: str = "OrgMemory"
    environment: str = "development"
    log_level: str = "INFO"
    api_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    sqlite_path: Path = ROOT / "data" / "runbook.db"
    generated_runbooks_dir: Path = ROOT / "generated_runbooks"
    repo_cache_dir: Path = ROOT / "data" / "repos"
    local_repo_mount: Path = Path("/workspace/local_repos")
    # Execution gets its own clone per run. The ingest cache is read to build
    # memory and must never be left dirty by an agent editing files in it.
    execution_dir: Path = ROOT / "data" / "executions"

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
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    google_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    xai_api_key: str = ""
    grok_model: str = "grok-4.5"
    kimi_api_key: str = ""
    kimi_model: str = "kimi-k2.6"
    kimi_base_url: str = "https://api.moonshot.ai/v1"
    org_memory_default_model_provider: str = "gpt"
    # A question is answered several independent ways and a judge picks the one
    # that actually fits what was asked. 1 disables the parallel pass entirely.
    org_memory_answer_candidates: int = 5
    org_memory_answer_judge_enabled: bool = True
    # When company memory holds nothing relevant and the question is not about
    # the company, answer from the model's own knowledge instead of refusing.
    org_memory_general_knowledge_enabled: bool = True
    # Autonomous execution. `executor` picks which headless coding agent applies
    # a handoff. Pushing is a separate switch because committing to a throwaway
    # local clone is reversible and publishing to a shared remote is not.
    org_memory_executor: str = "cursor"
    org_memory_execution_enabled: bool = True
    org_memory_execution_timeout_seconds: int = 900
    org_memory_execution_allow_push: bool = False
    org_memory_execution_branch_prefix: str = "orgmemory/"
    runbook_embedding_provider: str = "deterministic"
    runbook_embedding_model: str = "BAAI/bge-small-en-v1.5"
    runbook_openai_embedding_model: str = "text-embedding-3-large"
    runbook_reranker_provider: str = "deterministic"
    runbook_reranker_model: str = "Xenova/ms-marco-MiniLM-L-6-v2"
    runbook_embedding_cache_dir: Path = ROOT / "data" / "models"
    runbook_semantic_candidate_limit: int = 48
    runbook_embedding_batch_size: int = 16
    runbook_model_threads: int = 2
    assertion_auto_verify_enabled: bool = True
    assertion_auto_verify_days: int = 7

    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/auth/github/callback"
    github_oauth_use_pkce: bool = True
    github_token: str = ""
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/api/auth/slack/callback"
    slack_bot_token: str = ""
    integration_encryption_key: str = ""
    connector_vault_provider: str = "local"
    connector_kms_key_id: str = ""
    connector_kms_region: str = ""
    connector_oci_kms_crypto_endpoint: str = ""
    connector_oci_kms_auth: str = "instance-principal"
    connector_oci_config_profile: str = "DEFAULT"
    connector_manifest_public_keys_json: str = "{}"
    connector_sync_worker_enabled: bool = True
    connector_sync_poll_seconds: int = 2
    # How often standing organizational watches are re-evaluated.
    org_watch_poll_seconds: int = 120
    connector_custom_mcp_enabled: bool = True
    connector_custom_mcp_allow_private_networks: bool = False

    mcp_public_url: str = "http://localhost:8001"
    mcp_oauth_issuer_url: str = "http://localhost:8000"
    mcp_oauth_access_token_minutes: int = 60
    mcp_oauth_refresh_token_days: int = 30
    mcp_oauth_enable_dcr: bool = False

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = ""
    email_auth_enabled: bool = True
    email_code_ttl_minutes: int = 10
    email_code_resend_seconds: int = 45
    email_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = True
    nextauth_secret: str = ""
    jwt_secret: str = "runbook-local-dev-secret"
    app_base_url: str = "http://localhost:3000"
    auth_dev_mode: bool = True
    session_cookie_name: str = "runbook_session"
    session_cookie_domain: str = ""

    runbook_demo_mode: bool = False
    allow_local_command_execution: bool = False
    org_memory_enable_actions: bool = False
    org_memory_enable_procedures: bool = False
    org_memory_enable_advanced_reliability: bool = False
    org_memory_authority_order: str = (
        "current_code_config,approved_policy_decision,recent_authoritative_slack,"
        "merged_pull_request,open_issue,readme_documentation,old_slack,inferred_memory"
    )
    org_memory_change_interpreter_provider: str = "auto"
    org_memory_run_live_llm_tests: bool = False
    github_webhook_secret: str = ""

    @property
    def arcadedb_url(self) -> str:
        return f"http://{self.arcadedb_host}:{self.arcadedb_port}"

    def assert_safe_for_environment(self) -> None:
        """Refuse production startup with development trust boundaries."""
        if self.environment.casefold() != "production":
            return
        faults: list[str] = []
        if self.auth_dev_mode:
            faults.append("AUTH_DEV_MODE must be false")
        if self.jwt_secret == "runbook-local-dev-secret" or len(self.jwt_secret) < 32:
            faults.append("JWT_SECRET must be a non-default secret of at least 32 characters")
        if self.runbook_demo_mode:
            faults.append("RUNBOOK_DEMO_MODE must be false")
        if self.allow_local_command_execution:
            faults.append("ALLOW_LOCAL_COMMAND_EXECUTION must remain false")
        if not self.frontend_url.startswith("https://"):
            faults.append("FRONTEND_URL must use HTTPS")
        if not (
            self.github_client_id
            and self.github_client_secret
            or self.google_client_id
            and self.google_client_secret
            or self.email_auth_enabled
            and self.smtp_host
            and self.email_from
        ):
            faults.append(
                "At least one production sign-in provider (GitHub, Google, or email) "
                "must be configured"
            )
        if self.runbook_embedding_provider.casefold() == "deterministic":
            faults.append("RUNBOOK_EMBEDDING_PROVIDER must use fastembed or openai")
        vault_provider = self.connector_vault_provider.casefold()
        if vault_provider not in {"aws-kms", "oci-kms"} or not self.connector_kms_key_id:
            faults.append(
                "Production connector grants require CONNECTOR_VAULT_PROVIDER=aws-kms "
                "or oci-kms and CONNECTOR_KMS_KEY_ID"
            )
        if vault_provider == "oci-kms" and not self.connector_oci_kms_crypto_endpoint.startswith(
            "https://"
        ):
            faults.append("CONNECTOR_OCI_KMS_CRYPTO_ENDPOINT must use HTTPS")
        if not self.mcp_public_url.startswith("https://"):
            faults.append("MCP_PUBLIC_URL must use HTTPS")
        if not self.mcp_oauth_issuer_url.startswith("https://"):
            faults.append("MCP_OAUTH_ISSUER_URL must use HTTPS")
        if faults:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(faults))


settings = Settings()
