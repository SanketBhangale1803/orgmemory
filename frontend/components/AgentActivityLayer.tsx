"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type { WebMCPStatus } from "@/hooks/useOrgMemoryWebMCP";
import type { WebMCPActivity, WebMCPToolName } from "@/lib/webmcp";
import { WEBMCP_GOVERNED_TOOL_COUNT, WEBMCP_READ_TOOL_COUNT } from "@/lib/webmcpCatalog";

const targetForTool: Partial<Record<WebMCPToolName, string>> = {
  list_orgmemory_spaces: "spaces",
  ask_orgmemory: "canvas",
  inspect_orgmemory_changes: "trail",
  search_orgmemory: "memory",
  get_orgmemory_memory: "memory",
  get_orgmemory_related_memories: "trail",
  get_orgmemory_incidents: "memory",
  get_orgmemory_runbook: "canvas",
  get_orgmemory_service_context: "canvas",
  get_orgmemory_dependencies: "trail",
  get_orgmemory_decisions: "memory",
  propose_repository_refresh: "approval",
  list_orgmemory_approvals: "approval",
  resolve_orgmemory_approval: "approval",
  propose_orgmemory_memory: "approval",
  propose_orgmemory_incident: "approval",
  propose_orgmemory_decision: "approval",
  list_orgmemory_proposals: "approval",
  resolve_orgmemory_proposal: "approval",
};

const orbStatus: Partial<Record<WebMCPToolName, string>> = {
  list_orgmemory_spaces: "Orb is mapping memory spaces",
  ask_orgmemory: "Orb is investigating",
  inspect_orgmemory_changes: "Orb is inspecting recent changes",
  search_orgmemory: "Orb is searching organizational memory",
  get_orgmemory_memory: "Orb is reading the source-backed memory",
  get_orgmemory_related_memories: "Orb is connecting evidence",
  get_orgmemory_incidents: "Orb is comparing previous incidents",
  get_orgmemory_runbook: "Orb is checking the runbook",
  get_orgmemory_service_context: "Orb is assembling service context",
  get_orgmemory_dependencies: "Orb is tracing dependencies",
  get_orgmemory_decisions: "Orb is reviewing prior decisions",
  propose_repository_refresh: "Orb is waiting for approval",
  list_orgmemory_approvals: "Orb is checking approvals",
  resolve_orgmemory_approval: "Orb is recording your decision",
  propose_orgmemory_memory: "Orb is waiting for approval",
  propose_orgmemory_incident: "Orb is waiting for approval",
  propose_orgmemory_decision: "Orb is waiting for approval",
  list_orgmemory_proposals: "Orb is checking proposals",
  resolve_orgmemory_proposal: "Orb is recording your decision",
};

export function WebMCPStatusButton({
  status,
  toolCount,
  activity,
  onClick,
}: {
  status: WebMCPStatus;
  toolCount: number;
  activity?: WebMCPActivity;
  onClick: () => void;
}) {
  const live = Boolean(activity);
  const label = status === "ready"
    ? live
      ? "WebMCP agent connected"
      : "WebMCP ready"
    : status === "unsupported"
      ? "WebMCP browser needed"
      : status === "error"
        ? "WebMCP needs attention"
        : "Registering WebMCP";

  return (
    <button
      type="button"
      className={`wmcp-shell-badge ${status === "ready" ? "ready" : ""} ${live ? "live" : ""}`}
      onClick={onClick}
      aria-label={`${label}. Open WebMCP activity.`}
    >
      <span className="wmcp-spark" aria-hidden="true">✦</span>
      <span>{label}</span>
      {toolCount > 0 && <small>{toolCount} tools</small>}
    </button>
  );
}

export default function AgentActivityLayer({
  status,
  toolCount,
  activities,
  open,
  onClose,
  enabled,
  onEnabledChange,
  follow,
  onFollowChange,
}: {
  status: WebMCPStatus;
  toolCount: number;
  activities: WebMCPActivity[];
  open: boolean;
  onClose: () => void;
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  follow: boolean;
  onFollowChange: (enabled: boolean) => void;
}) {
  const latest = activities.at(-1);
  const [point, setPoint] = useState({ x: 32, y: 96 });
  const connected = activities.length > 0;

  useEffect(() => {
    if (!enabled || !latest) return;
    const targetName = targetForTool[latest.tool] || "canvas";
    const target = document.querySelector<HTMLElement>(`[data-orb-target="${targetName}"]`);
    if (!target) return;
    if (follow && latest.state === "running") {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    const move = () => {
      const bounds = target.getBoundingClientRect();
      setPoint({
        x: Math.max(28, Math.min(window.innerWidth - 28, bounds.left + bounds.width * 0.82)),
        y: Math.max(76, Math.min(window.innerHeight - 92, bounds.top + Math.min(54, bounds.height * 0.3))),
      });
    };
    move();
    window.addEventListener("resize", move);
    return () => window.removeEventListener("resize", move);
  }, [enabled, follow, latest]);

  const activityLabel = latest
    ? latest.state === "error"
      ? "Orb needs attention"
      : latest.state === "complete"
        ? latest.resultCount != null
          ? `Orb returned ${latest.resultCount} result${latest.resultCount === 1 ? "" : "s"}`
          : "Orb returned structured context"
        : orbStatus[latest.tool] || "Orb is working"
    : "Orb is ready";

  const activeCount = useMemo(
    () => activities.filter((activity) => activity.state === "running").length,
    [activities],
  );

  return (
    <>
      {enabled && latest && (
        <div
          className={`agent-orb-presence ${latest.state}`}
          style={{ "--orb-x": `${point.x}px`, "--orb-y": `${point.y}px` } as CSSProperties}
          aria-live="polite"
        >
          <span className="agent-orb-point" aria-hidden="true"><i />✦</span>
          <span className="agent-orb-label">{activityLabel}</span>
        </div>
      )}

      <div className={`wmcp-layer-scrim ${open ? "open" : ""}`} onClick={onClose} aria-hidden="true" />
      <aside className={`wmcp-activity-layer ${open ? "open" : ""}`} aria-hidden={!open} aria-label="WebMCP activity">
        <header className="wmcp-layer-head">
          <div>
            <p>Agent interface</p>
            <h2>WebMCP Activity</h2>
          </div>
          <button type="button" onClick={onClose} aria-label="Close WebMCP activity">×</button>
        </header>

        <section className="wmcp-connection-card">
          <span className={`wmcp-agent-beacon ${connected ? "connected" : ""}`} aria-hidden="true"><i />✦</span>
          <div>
            <strong>{connected ? "WebMCP Agent Connected" : status === "ready" ? "Ready for a browser agent" : "WebMCP unavailable"}</strong>
            <p>
              {connected
                ? `${activities.length} observable tool invocation${activities.length === 1 ? "" : "s"} in this page session.`
                : "The browser can discover structured organizational-memory tools without scraping this interface."}
            </p>
          </div>
          {activeCount > 0 && <em>{activeCount} live</em>}
        </section>

        <div className="wmcp-layer-metrics" aria-label="WebMCP tool summary">
          <div><strong>{toolCount || 19}</strong><span>exposed</span></div>
          <div><strong>{WEBMCP_READ_TOOL_COUNT}</strong><span>read-only</span></div>
          <div><strong>{WEBMCP_GOVERNED_TOOL_COUNT}</strong><span>governed</span></div>
        </div>

        <section className="wmcp-trace-section">
          <div className="wmcp-trace-head">
            <div><p>Browser agent → WebMCP → OrgMemory</p><strong>Live trace</strong></div>
            <span>{activities.length ? `${activities.length} calls` : "Waiting"}</span>
          </div>
          {activities.length ? (
            <ol className="wmcp-live-trace">
              {activities.map((activity, index) => (
                <li key={activity.id} className={activity.state}>
                  <span className="wmcp-trace-line" aria-hidden="true"><i /></span>
                  <div className="wmcp-call-index">{String(index + 1).padStart(2, "0")}</div>
                  <article>
                    <header>
                      <code>{activity.tool}</code>
                      <span>{activity.state === "running" ? "running" : activity.durationMs != null ? `${activity.durationMs} ms` : activity.state}</span>
                    </header>
                    <p>{activity.inputSummary}</p>
                    {activity.state === "complete" && (
                      <strong>
                        {activity.resultCount != null ? `${activity.resultCount} results · ` : ""}
                        {activity.resultSummary || "Structured result returned"}
                      </strong>
                    )}
                    {activity.message && <strong className="error">{activity.message}</strong>}
                    <details>
                      <summary>Developer details</summary>
                      <pre>{JSON.stringify({
                        tool: activity.tool,
                        permission: activity.permission,
                        arguments: activity.input,
                        state: activity.state,
                        result_count: activity.resultCount,
                        duration_ms: activity.durationMs,
                      }, null, 2)}</pre>
                    </details>
                  </article>
                </li>
              ))}
            </ol>
          ) : (
            <div className="wmcp-trace-empty">
              <span aria-hidden="true">✦</span>
              <strong>No agent calls yet</strong>
              <p>Ask a WebMCP-capable browser agent to search this workspace. Every real invocation will appear here.</p>
            </div>
          )}
        </section>

        <section className="wmcp-preferences">
          <div>
            <strong>Show Agent Activity</strong>
            <p>Keep Orb&rsquo;s movement and contextual status visible.</p>
          </div>
          <button type="button" role="switch" aria-checked={enabled} className={enabled ? "on" : ""} onClick={() => onEnabledChange(!enabled)}><i /></button>
          <div>
            <strong>Follow Orb</strong>
            <p>Bring the active evidence surface into view.</p>
          </div>
          <button type="button" role="switch" aria-checked={follow} className={follow ? "on" : ""} onClick={() => onFollowChange(!follow)}><i /></button>
        </section>

        <Link href="/webmcp" className="wmcp-command-link">
          Open WebMCP Command Center <span aria-hidden="true">↗</span>
        </Link>
      </aside>
    </>
  );
}
