# OrgMemory MCP server

`mcp_server/server.py` exposes the real OrgMemory HTTP API over FastMCP stdio. It does not contain canned answers: questions return authorized memory, evidence, a retrieval trace, and the persisted HCAG context envelope.

## Run

```bash
make mcp
python mcp_server/server.py --health
```

The legacy environment variables `RUNBOOK_API_URL` and `RUNBOOK_API_KEY` remain supported during migration. The default backend URL is `http://localhost:8000`.

## Company-memory tools

| Tool | Purpose |
|---|---|
| `orgmemory_ingest_github_repo` | Ingest repository evidence and extract atomic memory |
| `orgmemory_ingest_slack_channel` | Ingest source-backed team decisions and conventions |
| `orgmemory_upload_source` | Upload docs, reports, or pasted company knowledge |
| `orgmemory_ask` | Build a governed context envelope and answer with evidence |
| `orgmemory_search_memories` | Search current typed memory units |
| `orgmemory_get_company_profile` | Assemble the current company profile |
| `orgmemory_get_project_profile` | Assemble a project profile |
| `orgmemory_get_service_profile` | Assemble a service profile |
| `orgmemory_get_memory_graph` | Inspect real memory graph counts |
| `orgmemory_list_memory_conflicts` | List evidence-backed contradictions |
| `orgmemory_list_memory_updates` | List newer-to-older memory relationships |
| `orgmemory_list_source_revisions` | Inspect immutable source history |
| `orgmemory_list_change_sets` | Inspect semantic memory commits and impacts |
| `orgmemory_compile_skill` | Compile current policy/procedure memory into a versioned agent skill |
| `orgmemory_list_skills` | List current or stale skill specs |

## Cursor configuration

Create a workspace-scoped API key in **Settings → API keys**, then configure:

```json
{
  "mcpServers": {
    "orgmemory": {
      "command": "make",
      "args": ["-C", "/absolute/path/to/runbook", "mcp"],
      "env": {
        "RUNBOOK_API_URL": "http://localhost:8000",
        "RUNBOOK_API_KEY": "rbk_replace_with_a_new_workspace_key"
      }
    }
  }
}
```

Restart the MCP connection after saving. The bridge forwards the key as an `Authorization: Bearer` header. Workspace and team scope are enforced before retrieval; source-restricted memory cannot enter an agent's context envelope.

Useful prompts:

```text
Use OrgMemory to explain this repo before I edit it.
Use OrgMemory to find prior decisions about this service.
Use OrgMemory to retrieve current company context for this bug.
Use OrgMemory to list what changed and which agent skills became stale.
```

## Legacy compatibility

The previous `runbook_*` tools remain available temporarily for clients that have not migrated. Procedure extraction, action policies, approvals, and simulation are advanced compatibility features; they are not the primary OrgMemory product surface.
