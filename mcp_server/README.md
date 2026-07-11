# Runbook MCP server

This is a real MCP stdio server. It intentionally remains silent and waits when started directly; an MCP client owns its stdin/stdout lifecycle. Use `python server.py --health` for a command that checks the backend and exits.

Configure clients to run `make -C /absolute/path/to/runbook mcp`, or run the virtual environment command documented in the root README. The tools call the same Runbook API as the dashboard, so evidence grounding, AgentGate decisions, and audit history stay consistent.

## Tools

- `runbook_ingest_github_repo`
- `runbook_ingest_slack_channel`
- `runbook_upload_knowledge`
- `runbook_ask`
- `runbook_extract_runbooks`
- `runbook_list_runbooks`
- `runbook_get_runbook`
- `runbook_get_graph_summary`
- `runbook_get_service_graph`
- `runbook_get_blast_radius` — dependency blast radius from real graph edges
- `runbook_simulate_incident` — dry-run a runbook through the AgentGate policy; nothing executes
- `runbook_check_runbook_drift` — re-check runbook sources against current knowledge
- `runbook_propose_action`
- `runbook_list_pending_approvals`
- `runbook_get_audit_log`

## Client patterns

- Cursor / Claude Desktop: configure this directory as a stdio MCP server command.
- ChatGPT tools/connectors: expose the same backend endpoints through a connector manifest or hosted tool bridge.
- Slack bot: call `runbook_ask`, `runbook_extract_runbooks`, and approval tools from message actions.
- GitHub App: trigger `runbook_ingest_github_repo` from installation/repository webhooks.
- ClickUp/Jira automation: use `runbook_upload_knowledge` for ticket exports until live connectors are added.
