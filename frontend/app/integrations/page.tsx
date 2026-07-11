import Page from "@/components/Page";

const tools = [
  "runbook_ingest_github_repo", "runbook_ingest_slack_channel", "runbook_upload_knowledge",
  "runbook_ask", "runbook_extract_runbooks", "runbook_list_runbooks", "runbook_get_runbook",
  "runbook_propose_action", "runbook_list_pending_approvals", "runbook_get_audit_log",
];

export default function Integrations() {
  const config = JSON.stringify({mcpServers:{runbook:{command:"make",args:["-C","/path/to/runbook","mcp"]}}}, null, 2);
  return <Page title="MCP & integrations" description="Use the same governed capabilities from AI agents and developer tools."><div className="grid two"><section className="card"><div className="section-head"><h2>MCP tools</h2><span className="badge success">Available</span></div><div className="card-pad stack">{tools.map(tool=><div className="row between" key={tool}><code>{tool}</code><span className="badge">stdio</span></div>)}</div></section><section className="card card-pad stack"><div><h2>Connect an agent</h2><p className="subtle">The MCP server delegates to the Runbook API, so UI and agent actions share evidence, policy, and audit records.</p></div><pre className="trace">{config}</pre><div className="source"><strong>Supported clients</strong><p>Cursor, Claude Desktop, ChatGPT tools/connectors, Slack bots, GitHub Apps, and workflow automation can consume this boundary.</p></div></section></div></Page>;
}
