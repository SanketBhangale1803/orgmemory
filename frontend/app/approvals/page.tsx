"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, formatDate } from "@/lib/api";
import type { OrgMemoryRefreshRequest } from "@/lib/webmcp";

/* Decisions stay close to the work. This page shares the chat's chrome and
   visual language, and every request is decided in the same place it arrives:
   the workspace itself renders pending approvals inline, so most people never
   need to travel here at all. */

type Principal = {
  id: string;
  role: string;
  active_workspace_id: string;
  display_name?: string;
};

const REFRESH_STATES: Record<string, { label: string; tone: "info" | "success" | "danger" | "warning" }> = {
  queued: { label: "queued", tone: "info" },
  running: { label: "refreshing", tone: "info" },
  succeeded: { label: "completed", tone: "success" },
  failed: { label: "failed", tone: "danger" },
  denied: { label: "denied", tone: "warning" },
  pending_approval: { label: "pending approval", tone: "warning" },
};

export default function Approvals() {
  const [principal, setPrincipal] = useState<Principal>();
  const [requests, setRequests] = useState<OrgMemoryRefreshRequest[]>([]);
  const [connectorCalls, setConnectorCalls] = useState<any[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [busyId, setBusyId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    return Promise.all([
      api<OrgMemoryRefreshRequest[]>("/api/repository-refresh-requests")
        .then((items) => {
          setRequests(items);
        })
        .catch(() => undefined),
      api<any[]>("/api/connector-tool-calls").then(setConnectorCalls).catch(() => undefined),
      api<any[]>("/api/actions").then(setActions).catch(() => undefined),
    ]);
  }, []);

  useEffect(() => {
    api<Principal>("/api/auth/me").then(setPrincipal).catch(() => undefined);
    load();
    // The queue stays live without a refresh: an agent-resolved approval from a
    // WebMCP session disappears from this list within seconds.
    const timer = window.setInterval(load, 8000);
    return () => window.clearInterval(timer);
  }, [load]);

  const pending = useMemo(() => requests.filter((item) => item.status === "pending_approval"), [requests]);
  const isAdmin = principal?.role === "owner" || principal?.role === "admin";

  async function resolveRefresh(id: string, approved: boolean, who?: string) {
    setBusyId(id);
    setNote("");
    setError("");
    try {
      const result = await api<OrgMemoryRefreshRequest>(
        `/api/repository-refresh-requests/${encodeURIComponent(id)}/resolve`,
        { method: "POST", body: JSON.stringify({ approved }) },
      );
      setRequests((current) => current.map((item) => (item.id === result.id ? result : item)));
      setNote(
        approved
          ? `Approved — refreshing ${result.repository}. Memory updates when it lands.`
          : `Denied ${who ? `${who}'s request` : "the request"}.`,
      );
    } catch (exc: any) {
      setError(exc.message);
    } finally {
      setBusyId("");
    }
  }

  async function resolveAction(id: string, approved: boolean) {
    setBusyId(id);
    setNote("");
    setError("");
    try {
      const result: any = await api(`/api/actions/${approved ? "approve" : "deny"}`, {
        method: "POST",
        body: JSON.stringify({ action_id: id, resolved_by: "current-user" }),
      });
      setActions((current) => current.map((item) => (item.id === id ? result : item)));
      setNote(`Runbook action ${result.status}.`);
    } catch (exc: any) {
      setError(exc.message);
    } finally {
      setBusyId("");
    }
  }

  async function resolveConnector(id: string, approved: boolean) {
    setBusyId(id);
    setNote("");
    setError("");
    try {
      const result: any = await api(`/api/connector-tool-calls/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ approved }),
      });
      setConnectorCalls((current) =>
        current.map((item) => (item.id === id ? { ...item, ...result, id } : item)),
      );
      setNote(approved ? `Approved; connector call ${result.status}.` : "Connector call denied.");
    } catch (exc: any) {
      setError(exc.message);
    } finally {
      setBusyId("");
    }
  }

  return (
    <div className="ap-wrap">
      <header className="ap-head">
        <div>
          <h1>Approvals</h1>
          <p>
            Requests wait here for a human decision. Workspace admins can also decide them inline
            from the <Link href="/workspace">workspace</Link>.
          </p>
        </div>
        {pending.length > 0 && (
          <span className="ap-count">
            {pending.length} waiting
          </span>
        )}
      </header>

      {note && <div className="notice">{note}</div>}
      {error && <div className="notice error">{error}</div>}

      <section className="ap-card">
        <div className="ap-card-head">
          <div>
            <span className="panel-label">WebMCP proposal</span>
            <h2>Repository refresh requests</h2>
          </div>
          <span className={`badge ${pending.length ? "warning" : ""}`}>
            Human approval required
          </span>
        </div>
        {requests.length ? (
          requests.map((request) => {
            const state = REFRESH_STATES[request.status] || REFRESH_STATES.pending_approval;
            const canResolve =
              request.status === "pending_approval" &&
              Boolean(principal && (isAdmin || request.requested_by_id === principal.id));
            return (
              <article className="ap-row" key={request.id}>
                <div className="ap-row-main">
                  <div className="ap-row-body">
                    <strong>{request.project_name || request.repository}</strong>
                    <p>
                      <em>{request.requested_by_name || "A teammate"}</em>
                      {request.requested_by_email ? ` (${request.requested_by_email})` : ""} ·{" "}
                      &ldquo;{request.reason}&rdquo; · requested {formatDate(request.requested_at)}
                    </p>
                    {request.result?.files_scanned !== undefined && (
                      <small className="subtle">
                        {request.result.files_scanned} files scanned ·{" "}
                        {request.result.incremental?.sources_changed || 0} sources changed
                      </small>
                    )}
                    {request.error && <div className="notice error">{request.error}</div>}
                  </div>
                  <span className={`badge ${state.tone}`}>{state.label}</span>
                </div>
                {(canResolve || busyId === request.id) && (
                  <div className="ap-row-actions">
                    <button
                      className="button"
                      disabled={busyId === request.id}
                      onClick={() => void resolveRefresh(request.id, true)}
                    >
                      Approve &amp; refresh
                    </button>
                    <button
                      className="button danger"
                      disabled={busyId === request.id}
                      onClick={() => void resolveRefresh(request.id, false, request.requested_by_name)}
                    >
                      Deny
                    </button>
                  </div>
                )}
              </article>
            );
          })
        ) : (
          <div className="ap-empty">No repository refresh requests are waiting for approval.</div>
        )}
      </section>

      <section className="ap-card">
        <div className="ap-card-head">
          <div>
            <span className="panel-label">Connector gateway</span>
            <h2>External write requests</h2>
          </div>
          <span className="badge warning">Explicit approval</span>
        </div>
        {connectorCalls.length ? (
          connectorCalls.map((call) => (
            <article className="ap-row" key={call.id}>
              <div className="ap-row-main">
                <div className="ap-row-body">
                  <strong>
                    {call.provider}.{call.tool_name}
                  </strong>
                  <p>
                    Keys: {(call.arguments?.declared_keys || []).join(", ") || "none"} · values
                    redacted · requested {formatDate(call.requested_at)}
                  </p>
                  <code>{call.idempotency_key}</code>
                  {call.error && <div className="notice error">{call.error}</div>}
                </div>
                <span className="row">
                  <span className={`badge ${["high", "critical"].includes(call.risk_level) ? "danger" : "warning"}`}>
                    {call.risk_level}
                  </span>
                  <span className={`badge ${call.status === "succeeded" ? "success" : call.status === "failed" ? "danger" : "info"}`}>
                    {String(call.status).replace(/_/g, " ")}
                  </span>
                </span>
              </div>
              {call.status === "pending_approval" && (
                <div className="ap-row-actions">
                  <button
                    className="button"
                    disabled={busyId === call.id}
                    onClick={() => void resolveConnector(call.id, true)}
                  >
                    Approve &amp; execute
                  </button>
                  <button
                    className="button danger"
                    disabled={busyId === call.id}
                    onClick={() => void resolveConnector(call.id, false)}
                  >
                    Deny
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <div className="ap-empty">No connector writes are waiting for approval.</div>
        )}
      </section>

      <section className="ap-card">
        <div className="ap-card-head">
          <div>
            <span className="panel-label">Internal policy</span>
            <h2>Runbook actions</h2>
          </div>
        </div>
        {actions.length ? (
          actions.map((item) => (
            <article className="ap-row" key={item.id}>
              <div className="ap-row-main">
                <div className="ap-row-body">
                  <strong>{item.summary}</strong>
                  <p>
                    {item.reason} · requested {formatDate(item.requested_at)}
                  </p>
                  {item.command_preview && <code>{item.command_preview}</code>}
                </div>
                <span className="row">
                  <span className={`badge ${item.risk_score >= 80 ? "danger" : "warning"}`}>
                    {item.risk_score}/100
                  </span>
                  <span className="badge">{item.status}</span>
                </span>
              </div>
              {item.status === "pending" && (
                <div className="ap-row-actions">
                  <button
                    className="button"
                    disabled={busyId === item.id}
                    onClick={() => void resolveAction(item.id, true)}
                  >
                    Approve
                  </button>
                  <button
                    className="button danger"
                    disabled={busyId === item.id}
                    onClick={() => void resolveAction(item.id, false)}
                  >
                    Deny
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <div className="ap-empty">No runbook actions have been proposed.</div>
        )}
      </section>
    </div>
  );
}
