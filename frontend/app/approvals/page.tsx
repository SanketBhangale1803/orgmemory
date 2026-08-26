"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

export default function Approvals() {
  const [items, setItems] = useState<any[]>([]);
  const [connectorCalls, setConnectorCalls] = useState<any[]>([]);
  const [refreshRequests, setRefreshRequests] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = () => Promise.all([
    api<any[]>("/api/actions"),
    api<any[]>("/api/connector-tool-calls"),
    api<any[]>("/api/repository-refresh-requests"),
  ]).then(([actions, calls, refreshes]) => { setItems(actions); setConnectorCalls(calls); setRefreshRequests(refreshes); });

  useEffect(() => { load().catch((exc) => setError(exc.message)); }, []);

  async function resolveAction(id: string, approved: boolean) {
    try {
      const result: any = await api(`/api/actions/${approved ? "approve" : "deny"}`, {
        method: "POST", body: JSON.stringify({ action_id: id, resolved_by: "current-user" }),
      });
      setMessage(`Action ${result.status}.`); await load();
    } catch (exc: any) { setError(exc.message); }
  }

  async function resolveConnector(id: string, approved: boolean) {
    try {
      const result: any = await api(`/api/connector-tool-calls/${id}/resolve`, {
        method: "POST", body: JSON.stringify({ approved }),
      });
      setMessage(approved ? `Approved; connector call ${result.status}.` : "Connector call denied.");
      await load();
    } catch (exc: any) { setError(exc.message); }
  }

  async function resolveRefresh(id: string, approved: boolean) {
    try {
      const result: any = await api(`/api/repository-refresh-requests/${id}/resolve`, {
        method: "POST", body: JSON.stringify({ approved }),
      });
      setMessage(approved ? `Repository refresh ${result.status}.` : "Repository refresh denied.");
      await load();
    } catch (exc: any) { setError(exc.message); }
  }

  return <Page title="Approvals" description="Human decisions for every connector send, modify, purchase, or delete request.">
    {message && <div className="notice">{message}</div>}
    {error && <div className="notice error">{error}</div>}
    <section className="card" style={{ marginTop: message || error ? 16 : 0 }}>
      <div className="section-head"><div><span className="panel-label">WebMCP proposal</span><h2>Repository refresh requests</h2></div><span className="badge warning">Human approval required</span></div>
      {refreshRequests.length ? <table className="table"><thead><tr><th>Repository</th><th>Reason</th><th>Status</th><th>Requested</th><th>Decision</th></tr></thead><tbody>{refreshRequests.map((request) => <tr key={request.id}>
        <td><strong>{request.repository}</strong>{request.result?.files_scanned !== undefined && <div className="subtle">{request.result.files_scanned} files scanned · {request.result.incremental?.sources_changed || 0} sources changed</div>}{request.error && <div className="notice error">{request.error}</div>}</td>
        <td>{request.reason}</td>
        <td><span className={`badge ${request.status === "succeeded" ? "success" : request.status === "failed" ? "danger" : "warning"}`}>{request.status.replace(/_/g, " ")}</span></td>
        <td>{formatDate(request.requested_at)}</td>
        <td>{request.status === "pending_approval" ? <div className="row"><button className="button" onClick={() => resolveRefresh(request.id, true)}>Approve & refresh</button><button className="button danger" onClick={() => resolveRefresh(request.id, false)}>Deny</button></div> : <span className="subtle">{request.resolved_by || "—"}</span>}</td>
      </tr>)}</tbody></table> : <div className="empty">No WebMCP repository refresh requests are waiting for approval.</div>}
    </section>
    <section className="card" style={{ marginTop: 18 }}>
      <div className="section-head"><div><span className="panel-label">Connector gateway</span><h2>External write requests</h2></div><span className="badge warning">Explicit approval</span></div>
      {connectorCalls.length ? <table className="table"><thead><tr><th>Tool</th><th>Risk</th><th>Status</th><th>Requested</th><th>Decision</th></tr></thead><tbody>{connectorCalls.map((call) => <tr key={call.id}>
        <td><strong>{call.provider}.{call.tool_name}</strong><div className="subtle">Keys: {(call.arguments?.declared_keys || []).join(", ") || "none"} · values redacted</div><code>{call.idempotency_key}</code>{call.error && <div className="notice error">{call.error}</div>}</td>
        <td><span className={`badge ${["high","critical"].includes(call.risk_level) ? "danger" : "warning"}`}>{call.risk_level}</span></td>
        <td><span className={`badge ${call.status === "succeeded" ? "success" : call.status === "failed" ? "danger" : "info"}`}>{call.status.replace(/_/g," ")}</span></td>
        <td>{formatDate(call.requested_at)}</td>
        <td>{call.status === "pending_approval" ? <div className="row"><button className="button" onClick={() => resolveConnector(call.id, true)}>Approve & execute</button><button className="button danger" onClick={() => resolveConnector(call.id, false)}>Deny</button></div> : <span className="subtle">{call.resolved_by || "—"}</span>}</td>
      </tr>)}</tbody></table> : <div className="empty">No connector writes are waiting for approval.</div>}
    </section>
    <section className="card" style={{ marginTop: 18 }}>
      <div className="section-head"><div><span className="panel-label">Internal policy</span><h2>Runbook actions</h2></div></div>
      {items.length ? <table className="table"><thead><tr><th>Action</th><th>Risk</th><th>Status</th><th>Requested</th><th>Decision</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.summary}</strong><div className="subtle">{item.reason}</div>{item.command_preview && <code>{item.command_preview}</code>}</td><td><span className={`badge ${item.risk_score >= 80 ? "danger" : "warning"}`}>{item.risk_score}/100</span></td><td><span className="badge">{item.status}</span></td><td>{formatDate(item.requested_at)}</td><td>{item.status === "pending" ? <div className="row"><button className="button" onClick={() => resolveAction(item.id,true)}>Approve</button><button className="button danger" onClick={() => resolveAction(item.id,false)}>Deny</button></div> : <span className="subtle">{item.resolved_by || "—"}</span>}</td></tr>)}</tbody></table> : <div className="empty">No runbook actions have been proposed.</div>}
    </section>
  </Page>;
}
