# MCP Server

`mcp_server/server.py` is a FastMCP stdio server. Every tool calls the real
Runbook HTTP API — there are no canned MCP responses.

## Run

```bash
make mcp                      # creates mcp_server/.venv on first run
python mcp_server/server.py --health   # verify backend connectivity
```

Environment: `RUNBOOK_API_URL` (default `http://localhost:8000`).

## Tools

| Tool | Backend call |
|---|---|
| `runbook_ingest_github_repo` | `POST /api/ingest/github` |
| `runbook_ingest_slack_channel` | `POST /api/ingest/slack` |
| `runbook_upload_knowledge` | `POST /api/ingest/upload` |
| `runbook_ask` | `POST /api/ask` |
| `runbook_extract_runbooks` | `POST /api/runbooks/extract` |
| `runbook_list_runbooks` | `GET /api/runbooks` |
| `runbook_get_runbook` | `GET /api/runbooks/{id}` |
| `runbook_get_graph_summary` | `GET /api/projects/{id}/graph/summary` |
| `runbook_get_service_graph` | `GET /api/projects/{id}/graph/service/{name}` |
| `runbook_get_blast_radius` | `GET /api/projects/{id}/graph/blast-radius/{name}` |
| `runbook_simulate_incident` | `POST /api/simulate` |
| `runbook_check_runbook_drift` | `GET /api/runbooks/{id}/drift` or `GET /api/projects/{id}/drift` |
| `runbook_propose_action` | `POST /api/actions/propose` |
| `runbook_list_pending_approvals` | `GET /api/actions/pending` |
| `runbook_get_audit_log` | `GET /api/audit` |

## Client configuration

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "runbook": {
      "command": "/path/to/runbook/mcp_server/.venv/bin/python",
      "args": ["/path/to/runbook/mcp_server/server.py"],
      "env": { "RUNBOOK_API_URL": "http://localhost:8000" }
    }
  }
}
```

### Cursor

Add the same command under Settings → MCP. Cursor agents can then ask
Runbook questions, check drift, and propose actions that land in the
Approvals queue.

### ChatGPT tools / connectors

Wrap the HTTP API directly (OpenAPI at `/docs`) or bridge the stdio server;
the API surface is identical.

### Slack bot / GitHub App / ClickUp automation

Automation should call the HTTP API with an API key from `/api/keys`
(`Authorization: Bearer rbk_...`). Risky operations still flow through
AgentGate: a bot can *propose* a restart, but a human approves it in the
Approvals UI, and the audit log records both.

## Safety boundary

MCP tools never execute commands. `runbook_propose_action` creates a
policy-evaluated approval record; `runbook_simulate_incident` is a dry run.
`ALLOW_LOCAL_COMMAND_EXECUTION=false` ships as the default and no executor
exists in this release.
