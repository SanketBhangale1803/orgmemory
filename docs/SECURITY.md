# Security Model

## Authentication and sessions

- Application login is separate from source connectors. Google and GitHub identity
  login request identity scopes only; private source access is requested later
  from the Connectors domain. Passwordless email stores only a short-lived HMAC
  of the one-time code and consumes it once. Dev login (`AUTH_DEV_MODE=true`) is an explicit
  local-only fallback and issues the same User/Workspace/WorkspaceMember/Session rows.
- Browser sessions use a seven-day, HTTP-only, SameSite=Lax cookie. The server
  stores only the HMAC hash and expiry. Every `/api` route is authenticated by
  default except health checks and the minimum OAuth/login callback surface.
- Google and GitHub OAuth use PKCE plus an unguessable state. Connector flows bind the
  state to an intent, user, and workspace. States expire after ten minutes and
  are single-use.

## Secrets

- Connector grants are stored per workspace and encrypted at rest with Fernet.
  They are never returned to the browser. Production deployments should supply a
  KMS-managed `INTEGRATION_ENCRYPTION_KEY`.
- Git credentials are passed to `git clone` through a temporary askpass
  file and environment variable, not embedded in URLs or arguments.
- API keys (`/api/keys`) are shown once at creation; only a SHA-256 hash
  and a 12-character prefix are stored. Revocation is a tombstone so the
  audit trail survives. New keys are bound to the creator's active workspace;
  the MCP bridge forwards them as bearer credentials, and the API rejects
  keys that are unscoped, revoked, invalid, or used against another workspace.

## RBAC

Roles: `owner`, `admin`, `member`, `viewer`. Owners/admins manage the
workspace, connect sources, and approve sensitive actions; members ingest
and ask; viewers read.

## Action safety (AgentGate)

- Read, analysis, and draft actions are allowed. Mutations, external sends,
  deployments, production changes, database writes, infra changes,
  data exports, and customer-impacting actions require approval. Credential
  access fails closed unless admin approval is explicitly requested.
  Unknown action types fail closed.
- `ALLOW_LOCAL_COMMAND_EXECUTION=false` is the default. This release has no
  shell executor: approvals produce audit records and command previews
  only, and enabling the flag does not silently add execution.
- Simulation mode (`/api/simulate`) walks runbook steps through the same
  policy engine without creating actions, so teams can inspect what an
  agent would be allowed to do before granting anything.

## Ingestion hygiene

- Repository ingestion excludes dependency/build directories, binaries, and
  oversized files, and is capped by file count and size.
- Importers without credentials refuse to run (`not_connected`) instead of
  fabricating migrations.

## Audit

Every consequential event is recorded: ingestion jobs, queries answered,
runbook generation, drift checks, simulations, action proposals/approvals/
denials, memory approvals, importer runs, API key lifecycle, connector
connections and disconnections.
