"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const STAGES = [
  { id: "observed", label: "Observed", note: "Source event received" },
  { id: "interpreting", label: "Understood", note: "Semantic difference extracted" },
  { id: "reconciling", label: "Reconciled", note: "Belief history linked" },
  { id: "activating", label: "Activated", note: "Profiles refreshed" },
  { id: "ready", label: "Ready", note: "Context available to agents" },
];

function relationshipLabel(value: string) {
  return value === "INVALIDATES" ? "no longer true" : value.toLowerCase().replace(/_/g, " ");
}

export default function SemanticChangeDetail() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const value = await api<any>(`/api/memory/semantic-changes/${params.id}`);
        if (cancelled) return;
        setEvent(value);
        setError("");
        if (!["ready", "failed"].includes(value.status)) timer = setTimeout(load, 900);
      } catch (exc: any) {
        if (!cancelled) setError(exc.message);
      }
    };
    load();
    return () => { cancelled = true; if (timer) clearTimeout(timer); };
  }, [params.id]);

  const beliefs = useMemo(() => Object.fromEntries((event?.beliefs || []).map((belief: any) => [belief.id, belief])), [event]);
  const relationships = event?.result?.relationships || [];
  const stageIndex = event ? (event.status === "failed" ? -1 : Math.max(0, STAGES.findIndex(stage => stage.id === event.status))) : 0;

  return <Page
    eyebrow="Change intelligence / detail"
    title={event?.repository || "Understanding source change"}
    description={event ? `${event.event_type.replace(/_/g, " ")} · ${event.commit_sha ? event.commit_sha.slice(0, 10) : event.delivery_id.slice(0, 10)} · observed ${formatDate(event.created_at)}` : "Loading the source-backed change record…"}
    action={<Link className="button secondary" href="/updates">← Change feed</Link>}
  >
    {error && <div className="notice error">{error}</div>}
    {!event ? <div className="change-detail-loading"><div className="semantic-loader"><i/><i/><i/></div><strong>Loading semantic change…</strong></div> : <>
      <section className={`change-stage-rail ${event.status}`} aria-label="Semantic change processing stages">
        {STAGES.map((stage, index) => <div className={`change-stage ${index < stageIndex || event.status === "ready" ? "complete" : index === stageIndex ? "current" : ""}`} key={stage.id}>
          <span className="stage-node"><i>{index < stageIndex || event.status === "ready" ? "✓" : index + 1}</i></span>
          <div><strong>{stage.label}</strong><small>{stage.note}</small></div>
          {index < STAGES.length - 1 && <b />}
        </div>)}
      </section>

      {event.status === "failed" && <div className="notice error">OrgMemory could not interpret this change: {event.error}</div>}

      <section className="semantic-change-summary">
        <div>
          <span className="change-live"><i /> {event.status === "ready" ? "Memory activated" : `Currently ${event.status}`}</span>
          <h2>{event.result?.summary || "Reading the source diff and extracting atomic belief changes."}</h2>
          <div className="affected-areas">{(event.result?.affected_areas || []).map((area: string) => <span key={area}>{area}</span>)}</div>
        </div>
        <div className="summary-counts">
          <div><strong>{event.result?.counts?.added || 0}</strong><span>New</span></div>
          <div><strong>{event.result?.counts?.updated || 0}</strong><span>Updated</span></div>
          <div><strong>{event.result?.counts?.invalidated || 0}</strong><span>Retired</span></div>
          <div><strong>{event.result?.counts?.conflicts || 0}</strong><span>Conflicts</span></div>
        </div>
      </section>

      <div className="semantic-detail-grid">
        <section className="panel belief-transition-panel">
          <div className="panel-head"><div><span className="panel-label">Belief history</span><h2>What changed in company memory</h2></div><span>{relationships.length} linked transition{relationships.length === 1 ? "" : "s"}</span></div>
          <div className="belief-transition-list">
            {relationships.length ? relationships.map((relationship: any, index: number) => {
              const previous = beliefs[relationship.from_belief_id];
              const current = beliefs[relationship.to_belief_id];
              return <article className="belief-transition" key={relationship.id || `${relationship.from_belief_id}-${relationship.to_belief_id}`} style={{"--transition-delay": `${index * 110}ms`} as React.CSSProperties}>
                <div className="belief-card previous"><span>Previous belief</span><strong>{previous?.claim || current?.claim || "Company belief"}</strong><p>{previous?.current_value || "Previous value preserved in the belief ledger."}</p><small>{previous?.authority_tier?.replace(/_/g, " ")}</small></div>
                <div className="belief-relationship"><i/><b>{relationshipLabel(relationship.relationship)}</b><i/></div>
                <div className={`belief-card current ${current?.status || ""}`}><span>{relationship.relationship === "INVALIDATES" ? "Current state" : "Current belief"}</span><strong>{current?.claim || previous?.claim || "Company belief"}</strong><p>{current?.current_value || "New source-backed value"}</p><small>{Math.round(Number(current?.confidence || 0) * 100)}% confidence · {current?.authority_tier?.replace(/_/g, " ")}</small></div>
              </article>;
            }) : <div className="empty semantic-empty"><span>◎</span><strong>{event.status === "ready" ? "No prior belief was displaced" : "Belief reconciliation in progress"}</strong><p>{event.status === "ready" ? "This source change did not produce a linked update or invalidation above the confidence threshold." : "The transition will appear here as soon as source-backed beliefs are reconciled."}</p></div>}
          </div>
        </section>

        <aside className="agent-impact-panel">
          <div className="impact-orbit" aria-hidden="true"><i/><i/><span>AI</span></div>
          <span className="panel-label">Agent impact</span>
          <h2>What an agent should do differently</h2>
          <div className="impact-list">{(event.result?.agent_implications || []).map((implication: string, index: number) => <div key={implication} style={{"--impact-delay": `${index * 100 + 180}ms`} as React.CSSProperties}><span>{index + 1}</span><p>{implication}</p></div>)}{!(event.result?.agent_implications || []).length && <p className="subtle">No safe agent behavior change was inferred from this evidence.</p>}</div>
          <div className="profile-impact"><small>Context profiles refreshed</small>{(event.result?.affected_profiles || []).map((profile: string) => <span key={profile}>{profile.replace(/^[^:]+:/, "")}</span>)}</div>
          {event.source_url && <a className="button secondary" href={event.source_url} target="_blank" rel="noreferrer">Open source evidence ↗</a>}
        </aside>
      </div>
    </>}
  </Page>;
}
