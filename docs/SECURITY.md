# Security Model

## Authentication and sessions

- Application login is separate from source connectors. Dev login
  (`AUTH_DEV_MODE=true`) issues real User/Workspace/WorkspaceMember/Session
  rows; Google/GitHub/Microsoft env plumbing exists for provider-backed
  sessions issuing the same session model.
- Sessions are bearer tokens stored as hashes with expiry.
- OAuth states are random, expire after ten minutes, and are single-use.

## Secrets

- Connector tokens are verified against the provider before storage and
  encrypted at rest with Fernet. Production deployments should supply a
  KMS-managed `INTEGRATION_ENCRYPTION_KEY`.
- Git credentials are passed to `git clone` through a temporary askpass
  file and environment variable, not embedded in URLs or arguments.
- API keys (`/api/keys`) are shown once at creation; only a SHA-256 hash
  and a 12-character prefix are stored. Revocation is a tombstone so the
  audit trail survives.

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
connections.
