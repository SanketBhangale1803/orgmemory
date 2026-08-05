"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const STAGES = ["observed", "interpreting", "reconciling", "activating", "ready"];

function statusLabel(status: string) {
  return status === "ready" ? "Context active" : status.replace(/_/g, " ");
}

function ChangePulse({ status }: { status: string }) {
  const active = Math.max(0, STAGES.indexOf(status));
  return <div className="mini-change-pulse" aria-label={`Change status: ${status}`}>
    {STAGES.map((stage, index) => <span key={stage} className={index < active || status === "ready" ? "complete" : index === active ? "current" : ""} />)}
  </div>;
}

export default function Updates() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [events, setEvents] = useState<any[]>([]);
  const [changes, setChanges] = useState<any[]>([]);
  const [artifacts, setArtifacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
      else setLoading(false);
    }).catch(exc => { setError(exc.message); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!project) return;
    setLoading(true);
    Promise.all([
      api<any[]>(`/api/memory/semantic-changes?project_id=${encodeURIComponent(project)}`),
      api<any[]>(`/api/memory/change-sets?project_id=${encodeURIComponent(project)}`),
      api<any[]>(`/api/memory/artifacts?project_id=${encodeURIComponent(project)}`),
    ]).then(([nextEvents, nextChanges, nextArtifacts]) => {
      setEvents(nextEvents);
      setChanges(nextChanges);
      setArtifacts(nextArtifacts);
      setError("");
    }).catch(exc => setError(exc.message)).finally(() => setLoading(false));
  }, [project]);

  const totals = useMemo(() => events.reduce((sum, event) => {
    const counts = event.result?.counts || {};
    sum.understood += Number(counts.added || 0) + Number(counts.updated || 0) + Number(counts.invalidated || 0);
    sum.impacts += (event.result?.agent_implications || []).length;
    sum.conflicts += Number(counts.conflicts || 0);
    return sum;
  }, { understood: 0, impacts: 0, conflicts: 0 }), [events]);
  const stale = artifacts.filter(item => item.status === "stale");
  const processing = events.filter(event => !["ready", "failed"].includes(event.status)).length;

  return <Page
    eyebrow="Semantic change intelligence"
    title="Change Intelligence"
    description="OrgMemory watches source changes, understands their meaning, preserves belief history, and activates the updated context for agents."
    action={<select aria-label="Project" className="project-select" value={project} onChange={event => setProject(event.target.value)}>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>}
  >
    {error && <div className="notice error">{error}</div>}

    <section className="change-intelligence-hero">
      <div>
        <span className="change-live"><i /> {processing ? `${processing} change${processing === 1 ? "" : "s"} being understood` : "Company context is current"}</span>
        <h2>From source diff to active agent context.</h2>
        <p>A commit is more than changed lines. OrgMemory extracts what became true, links it to what was true before, and shows exactly what an agent should do differently.</p>
      </div>
      <div className="change-flow-preview" aria-hidden="true">
        <span>DIFF</span><i /><span>BELIEF</span><i /><span>CONTEXT</span>
        <b className="flow-signal" />
      </div>
    </section>

    <div className="change-metric-row">
      <div><span>Changes observed</span><strong>{events.length}</strong><small>GitHub deliveries</small></div>
      <div><span>Beliefs understood</span><strong>{totals.understood}</strong><small>Created, updated, or retired</small></div>
      <div><span>Agent implications</span><strong>{totals.impacts}</strong><small>Context changes agents can use</small></div>
      <div className={totals.conflicts ? "attention" : ""}><span>Needs judgment</span><strong>{totals.conflicts}</strong><small>Authority conflicts</small></div>
    </div>

    <div className="change-layout">
      <section className="panel semantic-feed">
        <div className="panel-head"><div><span className="panel-label">Semantic change feed</span><h2>What OrgMemory understood</h2></div><span>{events.length} observed</span></div>
        <div className="semantic-feed-body">
          {loading ? <div className="change-loading"><div className="memory-pulse"><i/><i/><i/></div><span>Loading company change history…</span></div> : events.length ? events.map((event, index) => {
            const counts = event.result?.counts || {};
            const summary = event.result?.summary || (event.status === "failed" ? event.error : "OrgMemory is interpreting this source change.");
            return <Link className={`semantic-event-card ${event.status}`} href={`/updates/${event.id}`} key={event.id} style={{"--event-delay": `${index * 45}ms`} as React.CSSProperties}>
              <div className="event-glyph"><span>{event.status === "ready" ? "✓" : event.status === "failed" ? "!" : "↻"}</span><i /></div>
              <div className="event-main">
                <div className="event-meta"><span className={`badge ${event.status === "ready" ? "success" : event.status === "failed" ? "danger" : "info"}`}>{statusLabel(event.status)}</span><small>{formatDate(event.created_at)}</small></div>
                <h3>{event.repository || "Company source"}</h3>
                <p>{summary}</p>
                <div className="event-foot"><code>{event.commit_sha ? event.commit_sha.slice(0, 8) : event.delivery_id.slice(0, 8)}</code><span>{Number(counts.added || 0)} new</span><span>{Number(counts.updated || 0)} updated</span><span>{Number(counts.invalidated || 0)} retired</span></div>
                <ChangePulse status={event.status} />
              </div>
              <b className="event-arrow">→</b>
            </Link>;
          }) : <div className="empty semantic-empty"><span>⌁</span><strong>No semantic changes observed yet</strong><p>Push a source change or connect a GitHub webhook. The first interpreted change will appear here with its belief history and agent impact.</p></div>}
        </div>
      </section>

      <aside className="change-sidebar">
        <section className="panel">
          <div className="panel-head"><div><span className="panel-label">Downstream readiness</span><h2>Agent context</h2></div></div>
          <div className="change-readiness">
            <div className={`readiness-ring ${stale.length ? "warning" : ""}`}><span>{stale.length ? "!" : "✓"}</span></div>
            <strong>{stale.length ? `${stale.length} artifact${stale.length === 1 ? "" : "s"} need review` : "Context is ready"}</strong>
            <p>{stale.length ? "A supporting memory changed. Review affected artifacts before an agent uses them." : "No dependent brief or skill is stale from the changes observed here."}</p>
          </div>
        </section>
        <section className="panel compact-ledger">
          <div className="panel-head"><div><span className="panel-label">Source revision ledger</span><h2>{changes.length} memory commits</h2></div></div>
          <div className="panel-body">{changes.slice(0, 4).map(change => <div className="ledger-mini" key={change.id}><i className={change.review_status === "needs_review" ? "warning" : ""}/><div><strong>{change.source_id.replace(/^.*?:/, "")}</strong><small>{change.added.length} added · {change.updated.length} updated · {change.invalidated.length} retired</small></div></div>)}{!changes.length && <div className="empty">No source revisions yet.</div>}</div>
        </section>
      </aside>
    </div>
  </Page>;
}
