"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const tone: Record<string, string> = { critical: "danger", high: "danger", medium: "warning", low: "success", stale: "danger", contradicted: "danger", possibly_stale: "warning" };

export default function ImpactDetail({params}:{params:Promise<{id:string}>}) {
  const {id} = use(params); const [impact,setImpact] = useState<any>(); const [error,setError] = useState("");
  function load(){ api<any>(`/api/change-impacts/${id}`).then(setImpact).catch(requestError => setError(requestError.message)); }
  useEffect(load,[id]);
  async function decide(assertionId:string, action:string) { const requiresReason = action !== "verify"; const reason = requiresReason ? window.prompt("Record the required rationale:") : "Verified against current evidence"; if (reason === null || !reason.trim()) return; try { const updated=await api<any>(`/api/assertions/${assertionId}/${action}`, {method:"POST", body:JSON.stringify({reason})}); setImpact((current:any)=>({...current,impacts:current.impacts.map((item:any)=>item.assertion_id===assertionId?{...item,status:updated.status}:item)})); } catch(requestError:any) { setError(requestError.message); } }
  if (!impact) return <Page title="Change impact" description="Loading evidence path…"><div className="card empty">{error || "Loading…"}</div></Page>;
  return <Page title="Change Impact" description={impact.summary} action={<span className={`badge ${tone[impact.severity]||"info"}`}>{impact.severity}</span>}>
    {error && <div className="notice error">{error}</div>}
    <section className="card card-pad stack"><div className="row between"><strong>{impact.change_type.replace(/_/g," ")} · {impact.change_ref}</strong><span className="subtle">{formatDate(impact.created_at)}</span></div><div><strong>Confirmed source evidence</strong><p className="subtle">{impact.changed.files.length ? impact.changed.files.join(", ") : "No changed file list was connected."}</p>{impact.changed.source_evidence.map((evidence:any,index:number)=><p className="source" key={index}>{evidence.detail || JSON.stringify(evidence)}</p>)}</div><div className="notice">{impact.evidence_limit}</div><p className="subtle">Runtime observability: {impact.observability.status}. {impact.observability.basis}</p></section>
    <section className="stack" style={{marginTop:16}}>{impact.impacts.length ? impact.impacts.map((item:any)=><article className="card" key={item.assertion_id}><div className="section-head"><div><h2>{item.assertion_title}</h2><p className="subtle">Affected service: {item.affected_service} · environment: {item.environment_scope} · reviewer: {item.verification_owner}</p></div><span className={`badge ${tone[item.severity]||"info"}`}>{item.severity}</span></div><div className="card-pad stack"><div className="source"><strong>Why this is affected</strong><p>{item.why_affected}</p><p className="subtle">{item.inference ? "Inference: runbook/service relationship, not proof that the procedure is invalid." : "Confirmed: direct graph path from changed source to assertion subject."}</p></div><div className="row"><button className="button secondary" onClick={()=>decide(item.assertion_id,"verify")}>Verify</button><button className="button secondary" onClick={()=>decide(item.assertion_id,"mark-stale")}>Mark stale</button><button className="button secondary" onClick={()=>decide(item.assertion_id,"supersede")}>Supersede</button><button className="button secondary" onClick={()=>decide(item.assertion_id,"dismiss")}>Dismiss</button><span className={`badge ${tone[item.status]||"warning"}`}>{item.status.replace(/_/g," ")}</span></div>{item.affected_runbook_ids.map((runbookId:string)=><Link className="subtle" href={`/runbooks/${runbookId}`} key={runbookId}>Open affected runbook →</Link>)}</div></article>) : <div className="card empty">No operational assertions are connected to this change. This is not evidence that no procedure is affected.</div>}</section>
  </Page>;
}
