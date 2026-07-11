# Runbook

> CI/CD for production runbooks: detect when code, configuration, or deployment changes make an operational procedure unsafe or stale.

Runbook is verified operational knowledge for production systems. It preserves cited answers, extraction, drift, simulation, approvals, audit, and MCP while adding graph-backed OperationalAssertions and change-impact review for repository and GitHub evidence. AgentGate evaluates every proposed action before anything crosses a read-only boundary.

This is not a chatbot over documents, and it is not another PagerDuty/Rootly/incident.io — those coordinate humans around incidents; Runbook models how the company's systems actually work and lets AI agents act on that knowledge safely (see `docs/COMPETITIVE_DIFFERENTIATION.md`). The durable output is an evidence-linked, machine-readable runbook with typed steps, source provenance, confidence, trust score, drift status, and approval rules.

Beyond ingestion, ask, and extraction, the platform includes:

- **Trust scoring** — every answer and runbook carries a trust score computed from source quality, ingestion recency, support breadth, and detected contradictions, with the reasoning shown.
- **Change-to-incident correlation** — incident questions automatically rank recently ingested PRs/issues by shared services, env vars, files, and error terms.
- **Runbook drift detection** — runbooks are re-checked against current knowledge (`fresh`, `possibly_stale`, `stale`, `conflicting_evidence`, `needs_human_review`) with per-signal detail.
- **Simulation mode** — dry-run any runbook (or a scenario like "Simulate Kafka outage for reddit_service") through the real AgentGate policy: per-step decisions, required approvals, dangerous steps, missing context. Nothing executes.
- **Blast radius** — dependency traversal over real graph edges: dependents, second-hop dependents, env vars, applicable runbooks.
- **Operational memory** — durable company rules derived only from ingested evidence, approval-gated, with graph provenance.
- **Incident-tool importers** — PagerDuty (live REST importer) plus scaffolded Rootly/incident.io/Opsgenie/Statuspage/JSM/ServiceNow interfaces that honestly report `Not connected`.
- **API keys** — hashed-at-rest keys for MCP clients and automation.
- **Benchmark reports** — HCAG's honest benchmark harness surfaced in-product (`/benchmarks`).

## Start the product

Prerequisites: Docker Desktop with at least 4 GB available, Docker Compose v2, and ports 3000, 8000, 2424, and 2480 free.

```bash
cd ~/Desktop/startup/runbook
cp .env.example .env
make runbook
```

`make runbook` runs in the foreground so service logs remain visible. Open [http://localhost:3000](http://localhost:3000). API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

In another terminal, load the demonstration corpus:

```bash
cd ~/Desktop/startup/runbook
make demo
```

If Docker reports that it cannot connect to `docker.sock`, start Docker Desktop first. This is a Docker daemon error, not a Runbook application error.

## Demo flow

1. Run `make runbook`, then `make demo` from a second terminal.
2. Open Login and use dev login, then open Overview and confirm Graph memory is connected.
3. Open Ask Runbook and select **Runbook Operations Demo**.
4. Ask `@runbook why is reddit_service failing?`.
5. Inspect the source evidence, HCAG retrieval trace, and Repo Graph.
6. Select **Extract runbook**, then open it from Runbooks.
7. Propose its restart step in the production environment.
8. Open Approvals and approve or deny it.
9. The audit event records the decision and the command preview. Commands are not executed in demo mode.
10. Open **Runbook Reliability**. Re-ingest the demo repository after changing a config file, inspect the resulting impact, and verify or mark the linked assertion stale with a rationale.

Demo files are not special-cased. `backend/scripts/load_demo.py` submits them to the same `IngestionService` used by uploads and external connectors. The grounding test ingests contradictory causes into separate projects, asks the same question, and verifies the cited answer changes.

## Architecture

```text
GitHub / Slack / uploads / logs / CI
                  │
                  ▼
        normalized ingestion + chunking
                  │
          ┌───────┴────────┐
          ▼                ▼
   HCAG context route   ArcadeDB graph memory
          └───────┬────────┘
                  ▼
       hybrid evidence ranking
                  │
       evidence-only reasoning
                  │
      structured cited runbooks
                  │
       AgentGate policy decision
                  │
        approval + audit history
```

- **ArcadeDB** is the source of truth for knowledge relationships: projects, repositories, directories, files, languages, packages, dependencies, services, environment variables, config keys, workflows, commands, endpoints, functions/classes, issues, PRs, Slack messages, chunks, runbooks, steps, and actions. The app talks to its HTTP API through `app/graph/arcade_client.py` and the `GraphStore` interface.
- **SQLite** stores local application state such as encrypted connector accounts, raw source content, generated runbook paths, approval status, and audit events. It does not replace graph retrieval.
- **HCAG** supplies query classification and context-window routing through a non-invasive adapter. Its routing logic is retained while persistence is implemented by Runbook's ArcadeDB graph store. A deterministic local planner keeps the product available if optional HCAG imports cannot load.
- **AgentGate** is loaded through an adapter and combined with Runbook's explicit action taxonomy. Read/analysis/draft operations are allowed; mutations, sends, deployments, production changes, and exports require approval; credential access fails closed.
- **Reasoning** uses an OpenAI-compatible model only when `OPENAI_API_KEY` is configured. The prompt is restricted to retrieved evidence. Without a key, the extractive reasoner ranks sentences and procedures from the same evidence. Both paths return the explicit insufficient-evidence response rather than inventing a cause.

## ArcadeDB

Docker Compose starts ArcadeDB and persists its databases in a named volume. Initialize or repair the schema independently with:

```bash
make arcade-init
make graph-check
curl http://localhost:8000/api/health/graph
```

Expected result:

```json
{"backend":"arcadedb","connected":true,"database":"runbook","node_counts":{},"edge_counts":{}}
```

Vertex/edge types and indexes are idempotently created from `backend/app/graph/migrations.py`.

Open ArcadeDB Studio at [http://localhost:2480](http://localhost:2480). Use:

- Server: `localhost`
- Port: `2480`
- User: `root`
- Password: `runbook_dev_password` unless changed in `.env`
- Database: `runbook`

The Runbook UI also exposes a Repo Graph page with real graph counts, service map, file references, edge table, and graph node table from `/api/projects/{project_id}/graph/*`.

## Application auth and workspaces

Runbook separates application login from source connector authorization. Local development supports dev login:

```bash
curl -X POST http://localhost:8000/api/auth/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@runbook.local","display_name":"Demo User"}'
```

This creates a real `User`, `Workspace`, `WorkspaceMember`, and `Session` record. Workspace endpoints are:

- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/workspaces`
- `POST /api/workspaces`
- `GET /api/workspaces/{workspace_id}/members`
- `POST /api/workspaces/{workspace_id}/members/invite`

Roles are `owner`, `admin`, `member`, and `viewer`. Dev mode is controlled by `AUTH_DEV_MODE=true`. Google, GitHub, and Microsoft/Entra ID environment variables are present so provider-backed sessions can issue the same backend session model.

## GitHub authentication and ingestion

### OAuth connection

Create a GitHub OAuth App with callback URL:

```text
http://localhost:8000/api/auth/github/callback
```

Set `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` in `.env`, restart the backend, then select **Connect with GitHub** on Connectors. The requested `repo read:org` scopes allow private repository discovery for the authenticated user. Organizations with SAML SSO or third-party application restrictions may require the user or an organization owner to authorize the OAuth application. Runbook only sees repositories the authenticated identity is allowed to access.

For local development, select **Use token** and enter a fine-grained personal access token, or set `GITHUB_TOKEN`. The token is verified before encrypted storage.

Ingest from the UI or API:

```bash
curl -X POST http://localhost:8000/api/ingest/github \
  -H 'Content-Type: application/json' \
  -d '{"repo_url_or_path":"https://github.com/org/repo","project_name":"Service platform"}'
```

The scanner covers documentation, CI workflows, compose files, Jenkinsfiles, package manifests, configuration, source files, endpoints, imports, functions/classes, env vars, commands, errors, and operational text/log formats. Authenticated GitHub repositories also include issues and pull requests with original URLs. Secrets are passed to Git using a temporary askpass helper and are not embedded in clone URLs or process arguments. Docker Compose mounts `~/Desktop/startup` read-only at `/workspace/local_repos`, and the path adapter maps inputs such as `~/Desktop/startup/hcag` into that mount; local development opens the original path directly.

Repository ingestion is job-recorded. Use:

```bash
curl http://localhost:8000/api/ingest/jobs
curl http://localhost:8000/api/ingest/jobs/job_...
```

The UI exposes the same data on **Ingestion Jobs**, including status, progress, files/issues/PRs scanned, graph nodes/edges written, warnings, and errors.

## Slack authentication and ingestion

Create a Slack app with redirect URL:

```text
http://localhost:8000/api/auth/slack/callback
```

Configure `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET`, restart, and use **Connect with Slack**. The OAuth flow requests channel discovery and public/private history scopes. The app must be invited to private channels. A bot token can be verified and stored through the UI or `SLACK_BOT_TOKEN`.

After connection, list channels at `GET /api/connectors/slack/channels` and ingest one:

```bash
curl -X POST http://localhost:8000/api/ingest/slack \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"prj_...","channel_id":"C012345","limit":200}'
```

Pasted Slack exports work without OAuth through Ingest or `POST /api/ingest/upload`. Gmail, ClickUp, Jira, Linear, Notion, Google Drive, and Zendesk have connector registry entries and planned UI states without pretending live access exists.

## Asking and retrieval

```bash
curl -X POST http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"prj_...","query":"@runbook why is reddit_service failing?"}'
```

The response contains the likely cause, confidence, related services, related files, related issues, related pull requests, evidence snippets and URLs, suggested runbooks, safe and approval-required actions, and a retrieval trace with HCAG route, context window, chunk IDs, graph paths, and routing engine. Related files, issues, and pull requests are derived only from the ranked evidence the retrieval pass actually surfaced. Every supported answer includes at least one citation. Unsupported answers return:

```text
I do not have enough evidence to answer this confidently.
```

## Runbook extraction and approvals

`POST /api/runbooks/extract` retrieves current evidence, extracts source procedures and commands, classifies each action, and writes YAML and JSON to `generated_runbooks/{project_id}/`. Extraction returns zero runbooks when sources contain no executable procedure.

`POST /api/actions/propose` resolves a real runbook step, renders its command preview, evaluates AgentGate, and creates an audit record. Use `/api/actions/approve` or `/api/actions/deny` for pending requests. With the safe defaults below, approved commands remain previews:

```env
RUNBOOK_DEMO_MODE=true
ALLOW_LOCAL_COMMAND_EXECUTION=false
```

The current release deliberately does not implement a shell executor. Enabling the environment flag does not silently broaden execution; a future isolated executor must be added explicitly.

## MCP server

Install and run for an MCP client:

```bash
make mcp
```

An MCP stdio process is supposed to remain silent and wait for its client. It is not hung. To verify dependencies and backend connectivity without waiting:

```bash
source mcp_server/.venv/bin/activate
python mcp_server/server.py --health
```

The server exposes:

- `runbook_ingest_github_repo`
- `runbook_ingest_slack_channel`
- `runbook_upload_knowledge`
- `runbook_ask`
- `runbook_extract_runbooks`
- `runbook_list_runbooks`
- `runbook_get_runbook`
- `runbook_get_graph_summary`
- `runbook_get_service_graph`
- `runbook_get_blast_radius`
- `runbook_simulate_incident`
- `runbook_check_runbook_drift`
- `runbook_propose_action`
- `runbook_list_pending_approvals`
- `runbook_get_audit_log`

See `mcp_server/README.md` and `docs/MCP.md` for client configuration. The boundary is suitable for Cursor, Claude Desktop, ChatGPT tools/connectors, Slack bots, Gmail assistants, GitHub Apps, and workflow automation.

## Local development

```bash
# Terminal 1: graph
docker compose up -d arcadedb
make arcade-init

# Terminal 2: API (creates backend/.venv on first run)
make backend

# Terminal 3: UI (installs dependencies on first run)
make frontend
```

Quality commands:

```bash
make test
make lint
make ci        # test, lint/type-check, and production frontend build
make format
make reset
make docker-down
make benchmark    # runs the HCAG benchmark harness in ../hcag
```

## Repository automation

GitHub Actions runs `make ci` for every push and pull request. Dependabot opens
weekly updates for Python packages, npm packages, and GitHub Actions. Local
state, generated runbooks, dependency directories, and `.env` stay out of the
repository through `.gitignore`; use `.env.example` as the safe configuration
template.

## Drift, simulation, correlation, and blast radius

```bash
# drift for one runbook or a whole project
curl http://localhost:8000/api/runbooks/rb_.../drift
curl http://localhost:8000/api/projects/prj_.../drift

# dry-run a runbook through the real policy engine
curl -X POST http://localhost:8000/api/simulate \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"prj_...","scenario":"Simulate Kafka outage for reddit_service"}'

# rank recent changes against the current failure evidence
curl -X POST http://localhost:8000/api/correlate \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"prj_...","service_name":"reddit_service"}'

# dependency blast radius from real graph edges
curl http://localhost:8000/api/projects/prj_.../graph/blast-radius/reddit_service
```

Operational memories are managed at `GET/POST /api/projects/{id}/memories`
(`/derive`, then `/api/memories/{id}/approve|reject`), importers at
`GET /api/importers` and `POST /api/importers/{name}/import`, and API keys
at `GET/POST/DELETE /api/keys`. Documentation lives in `docs/`
(`ARCHITECTURE.md`, `GRAPH_MODEL.md`, `SECURITY.md`, `CONNECTORS.md`,
`RUNBOOK_EXTRACTION.md`, `APPROVALS.md`, `MCP.md`, `BENCHMARKS.md`,
`COMPETITIVE_DIFFERENTIATION.md`, `HCAG_BENCHMARK_PLAN.md`).

## Environment reference

Copy `.env.example`. The required local graph values are:

```env
ARCADEDB_HOST=arcadedb
ARCADEDB_PORT=2480
ARCADEDB_USER=root
ARCADEDB_PASSWORD=runbook_dev_password
ARCADEDB_DATABASE=runbook
GRAPH_BACKEND=arcadedb
```

Connector tokens stored through the UI are encrypted with Fernet. Set `INTEGRATION_ENCRYPTION_KEY` to a stable generated key outside local demos; otherwise a permission-restricted key file is generated beside the SQLite database.

## Known limitations

- Repository scanning is capped by file count and file size and intentionally excludes binaries, dependency folders, and build artifacts.
- GitHub pagination currently covers the first 100 issues and 50 pull requests per repository.
- Slack ingestion resolves message text and permalinks but does not yet enrich user IDs to profile names.
- Retrieval is lexical plus graph/service weighting. Embeddings can be added behind the retrieval interface without changing response contracts.
- Connector secrets are appropriate for a single-machine deployment; production should use a cloud KMS and managed relational database.
- No command executor ships in this release. All action commands are policy-evaluated previews.

## Roadmap

Near-term work is GitHub App installation for organization-wide repository selection, incremental webhook ingestion, managed secret storage, embedding-backed hybrid ranking, Slack event subscriptions, and isolated executor workers with short-lived credentials. The connector, graph, retrieval, and action interfaces are already separated for those additions.
