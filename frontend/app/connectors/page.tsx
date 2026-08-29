"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import IdeAccess from "@/components/IdeAccess";
import Page from "@/components/Page";
import { API, api, formatDate } from "@/lib/api";

const sampleTools = JSON.stringify([
  {
    name: "search",
    description: "Search this MCP server",
    kind: "read",
    risk_level: "low",
    input_schema: { type: "object", properties: { query: { type: "string" } } },
  },
], null, 2);

function monogram(name: string) {
  return name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();
}

export default function Connectors() {
  const [items, setItems] = useState<any[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [coverage, setCoverage] = useState<any>();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [registering, setRegistering] = useState(false);
  const [custom, setCustom] = useState({
    name: "", serverUrl: "", version: "1.0.0", clientId: "",
    authorizationUrl: "", tokenUrl: "", scopes: "read", tools: sampleTools,
  });

  const load = () => Promise.all([
    api<any[]>("/api/connectors"),
    api<any[]>("/api/connectors/catalog"),
    api("/api/connectors/coverage"),
  ]).then(([connections, directory, nextCoverage]) => {
    setItems(connections);
    setCatalog(directory);
    setCoverage(nextCoverage);
  });

  useEffect(() => {
    load().catch((exc) => setError(exc.message));
    const params = new URLSearchParams(window.location.search);
    if (params.get("connected")) setMessage("Connector authorized successfully.");
    if (params.get("error")) setError(params.get("error")!);
  }, []);

  const categories = useMemo(
    () => Array.from(new Set(catalog.map((item) => item.category).filter(Boolean))),
    [catalog],
  );

  async function disconnect(item: any) {
    const name = item.manifest?.name || item.provider;
    if (!window.confirm(`Disconnect ${name} for your delegated account?`)) return;
    try {
      await api(`/api/connectors/${encodeURIComponent(item.provider)}`, { method: "DELETE" });
      setMessage(`${name} disconnected.`);
      await load();
    } catch (exc: any) { setError(exc.message); }
  }

  async function revokeRegistration(provider: string) {
    if (!window.confirm("Revoke this custom MCP registration for the whole workspace?")) return;
    try {
      await api(`/api/connectors/custom/registrations/${encodeURIComponent(provider)}`, { method: "DELETE" });
      setMessage("Custom MCP registration revoked.");
      await load();
    } catch (exc: any) { setError(exc.message); }
  }

  async function registerCustom(event: FormEvent) {
    event.preventDefault();
    setRegistering(true); setError("");
    try {
      const tools = JSON.parse(custom.tools);
      await api("/api/connectors/custom/registrations", {
        method: "POST",
        body: JSON.stringify({
          name: custom.name,
          server_url: custom.serverUrl,
          version: custom.version,
          oauth: {
            client_id: custom.clientId,
            authorization_url: custom.authorizationUrl,
            token_url: custom.tokenUrl,
            scopes: custom.scopes.split(/[\s,]+/).filter(Boolean),
            pkce_required: true,
          },
          manifest: { icon: "plug", resources: [], tools },
        }),
      });
      setMessage("Custom MCP server pinned. Connect it to authorize your own account.");
      setCustom((value) => ({ ...value, name: "", serverUrl: "", clientId: "" }));
      await load();
    } catch (exc: any) { setError(exc.message); }
    finally { setRegistering(false); }
  }

  return <Page eyebrow="Connector gateway" title="Connect your company" description="Verified packages, custom remote MCP servers, and local extensions share one signed manifest, delegated OAuth, sync, approval, and audit boundary.">
    {message && <div className="notice">{message}</div>}
    {error && <div className="notice error">{error}</div>}

    <div className="connector-grid">{items.map((item) => {
      const manifest = item.manifest || {};
      const account = item.accounts?.find((candidate: any) => candidate.status === "connected");
      const readTools = (manifest.tools || []).filter((tool: any) => tool.kind === "read");
      const writeTools = (manifest.tools || []).filter((tool: any) => tool.kind === "write");
      const provider = encodeURIComponent(item.provider);
      return <section className={`connector-card ${item.connected ? "connected" : ""}`} key={item.provider}>
        <div className="connector-card-head">
          <span className="connector-logo">{monogram(manifest.name || item.provider)}</span>
          <span className={`connection-state ${item.connected ? "online" : ""}`}><i/>{item.connected ? "Connected" : "Not connected"}</span>
        </div>
        <div><h2>{manifest.name || item.provider}</h2><p>{manifest.execution_mode} connector · pinned at {manifest.version}</p></div>
        <div className="permission-list">
          {(manifest.resources || []).map((resource: any) => <span key={resource.type}><i>✓</i>{resource.label}</span>)}
          <span><i>R</i>{readTools.length} read tool{readTools.length === 1 ? "" : "s"}</span>
          <span><i>W</i>{writeTools.length} approval-gated write tool{writeTools.length === 1 ? "" : "s"}</span>
        </div>
        {account && <div className="connected-account"><span>Delegated account</span><strong>{account.display_name}</strong><small>Updated {formatDate(account.updated_at)}</small></div>}
        <div className="connector-actions">
          {item.connected ? <>
            <a className="button secondary" href={`${API}/api/connectors/${provider}/auth/start`}>Reconnect</a>
            <button className="text-button danger-text" onClick={() => disconnect(item)}>Disconnect mine</button>
          </> : <a className="button" href={`${API}/api/connectors/${provider}/auth/start`}>Connect {manifest.name || item.provider}</a>}
          {item.provider.startsWith("custom.") && <button className="text-button danger-text" onClick={() => revokeRegistration(item.provider)}>Revoke package</button>}
        </div>
        <small className="provider-note">Manifest {String(manifest.signature || "").slice(0, 12)}… · connector content is isolated as untrusted data.</small>
      </section>;
    })}</div>

    <IdeAccess />

    <section className="card card-pad stack" style={{ marginTop: 18 }}>
      <div className="section-head"><div><span className="panel-label">Third connector category</span><h2>Register a remote MCP server</h2></div><span className="badge warning">Admin</span></div>
      <p className="subtle">OrgMemory pins its URL, version, OAuth settings, and tool manifest. Private-network and non-HTTPS targets are rejected by the cloud gateway.</p>
      <form className="stack" onSubmit={registerCustom}>
        <div className="grid two"><label className="field"><span>Name</span><input required value={custom.name} onChange={(event) => setCustom({...custom, name:event.target.value})}/></label><label className="field"><span>Streamable HTTP URL</span><input required type="url" placeholder="https://connector.example/mcp" value={custom.serverUrl} onChange={(event) => setCustom({...custom, serverUrl:event.target.value})}/></label></div>
        <div className="grid two"><label className="field"><span>OAuth authorization URL</span><input required type="url" value={custom.authorizationUrl} onChange={(event) => setCustom({...custom, authorizationUrl:event.target.value})}/></label><label className="field"><span>OAuth token URL</span><input required type="url" value={custom.tokenUrl} onChange={(event) => setCustom({...custom, tokenUrl:event.target.value})}/></label></div>
        <div className="grid two"><label className="field"><span>OAuth client ID</span><input required value={custom.clientId} onChange={(event) => setCustom({...custom, clientId:event.target.value})}/></label><label className="field"><span>Least-privilege scopes</span><input required value={custom.scopes} onChange={(event) => setCustom({...custom, scopes:event.target.value})}/></label></div>
        <label className="field"><span>Pinned tools (JSON)</span><textarea rows={10} value={custom.tools} onChange={(event) => setCustom({...custom, tools:event.target.value})}/></label>
        <button className="button" disabled={registering}>{registering ? "Validating…" : "Register and pin MCP server"}</button>
      </form>
    </section>

    <section className="platform-catalog">
      <div className="section-head"><div><span className="panel-label">Connector directory</span><h2>Built-in, remote, and local</h2></div><span>Installed capability is explicit</span></div>
      <div className="platform-catalog-body">{categories.map((category) => <div className="platform-category" key={category}>
        <h3>{category}</h3><div>{catalog.filter((item) => item.category === category).map((item) => <article key={item.provider}>
          <span>{monogram(item.label)}</span><div><strong>{item.label}</strong><small>{(item.memory || []).join(" · ")}</small></div>
          <em className={item.status}>{item.status === "live" ? "Available" : item.status === "next" ? "SDK ready" : "Directory"}</em>
        </article>)}</div>
      </div>)}</div>
    </section>

    <section className="security-callout"><div><span className="panel-label">Credential boundary</span><h2>One person, one delegated grant</h2></div><p>OAuth tokens never reach the browser. Production uses KMS envelope encryption bound to workspace, user, and provider. Every write carries an idempotency key, waits for approval, and produces an audit event.</p></section>
    {coverage && <section className="coverage-panel"><div className="section-head"><div><span className="panel-label">Index coverage</span><h2>Exactly what OrgMemory can search</h2></div><span className="badge success">Scoped</span></div><div className="coverage-grid">{coverage.sources.map((source:any) => <article key={source.provider}><div className="row between"><strong>{source.provider}</strong><span>{source.connected ? "Connected" : "Not connected"}</span></div><dl>{Object.entries(source.indexed).map(([name,value]:any) => <div key={name}><dt>{name.replace(/_/g," ")}</dt><dd>{value}</dd></div>)}</dl><small>Refresh: {source.refresh_mode}</small></article>)}</div></section>}
  </Page>;
}
