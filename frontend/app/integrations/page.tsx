"use client";

import { FormEvent, useState } from "react";
import Page from "@/components/Page";
import { API, api } from "@/lib/api";

const readTools = ["orgmemory_ask", "orgmemory_search_memories", "orgmemory_get_company_profile", "orgmemory_get_memory_graph", "orgmemory_list_source_revisions"];
const writeTools = ["orgmemory_request_connector_action"];

export default function Integrations() {
  const [name, setName] = useState("Claude / ChatGPT");
  const [redirectUri, setRedirectUri] = useState("");
  const [write, setWrite] = useState(false);
  const [registration, setRegistration] = useState<any>();
  const [error, setError] = useState("");
  const publicMcp = process.env.NEXT_PUBLIC_MCP_URL || "http://localhost:8001/mcp";

  async function register(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      setRegistration(await api("/api/mcp/oauth/clients", {
        method: "POST",
        body: JSON.stringify({ name, redirect_uris: [redirectUri], scopes: write ? ["read", "write"] : ["read"] }),
      }));
    } catch (exc: any) { setError(exc.message); }
  }

  const localConfig = JSON.stringify({
    mcpServers: {
      orgmemory: {
        command: "make", args: ["-C", "/absolute/path/to/orgmemory", "mcp"],
        env: { RUNBOOK_API_URL: API, RUNBOOK_API_KEY: "om_replace_with_workspace_key" },
      },
    },
  }, null, 2);

  return <Page title="MCP & integrations" description="Consume OrgMemory itself as a remote OAuth connector, or run the same boundary locally over stdio.">
    {error && <div className="notice error">{error}</div>}
    <div className="grid two">
      <section className="card card-pad stack">
        <div className="section-head"><div><span className="panel-label">Remote Streamable HTTP</span><h2>{publicMcp}</h2></div><span className="badge success">OAuth</span></div>
        <p className="subtle">Use this URL in Claude custom connectors, ChatGPT developer mode, Codex, or any MCP client that supports remote Streamable HTTP.</p>
        <dl className="clean-details"><div><dt>Authorization server</dt><dd>{API}</dd></div><div><dt>OAuth metadata</dt><dd>{API}/.well-known/oauth-authorization-server</dd></div><div><dt>Protected resource</dt><dd>{API}/.well-known/oauth-protected-resource</dd></div></dl>
        <div className="notice"><strong>Write scope creates requests, not side effects.</strong><br/>The remote agent can request an action, but a person must approve it in OrgMemory before the connector executes it.</div>
      </section>
      <section className="card card-pad stack">
        <div><span className="panel-label">OAuth client</span><h2>Register a consuming agent</h2></div>
        <form className="stack" onSubmit={register}><label className="field"><span>Client name</span><input required value={name} onChange={(event) => setName(event.target.value)}/></label><label className="field"><span>Exact redirect URI</span><input required type="url" placeholder="https://client.example/oauth/callback" value={redirectUri} onChange={(event) => setRedirectUri(event.target.value)}/></label><label className="row"><input type="checkbox" checked={write} onChange={(event) => setWrite(event.target.checked)}/> Allow approval-request tools (write scope)</label><button className="button">Register OAuth client</button></form>
        {registration && <pre className="trace">{JSON.stringify(registration, null, 2)}</pre>}
      </section>
    </div>
    <div className="grid two" style={{ marginTop: 18 }}>
      <section className="card"><div className="section-head"><h2>Read tools</h2><span className="badge success">read</span></div><div className="card-pad stack">{readTools.map((tool) => <div className="row between" key={tool}><code>{tool}</code><span className="badge">untrusted sources isolated</span></div>)}</div></section>
      <section className="card"><div className="section-head"><h2>Write-request tools</h2><span className="badge warning">write</span></div><div className="card-pad stack">{writeTools.map((tool) => <div className="row between" key={tool}><code>{tool}</code><span className="badge warning">approval + idempotency</span></div>)}</div></section>
    </div>
    <section className="card card-pad stack" style={{ marginTop: 18 }}><div><span className="panel-label">Local bridge</span><h2>stdio configuration</h2><p className="subtle">For local agents, use a revocable workspace API key. Remote HTTP never falls back to this key.</p></div><pre className="trace">{localConfig}</pre></section>
  </Page>;
}
