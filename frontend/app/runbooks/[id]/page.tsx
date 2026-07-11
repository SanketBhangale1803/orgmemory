"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const driftBadge: Record<string, string> = {
  fresh: "success",
  unchecked: "",
  possibly_stale: "warning",
  needs_human_review: "warning",
  conflicting_evidence: "danger",
  stale: "danger",
};

export default function Detail({params}:{params:Promise<{id:string}>}) {
  const {id} = use(params);
  const [item,setItem]=useState<any>();
  const [action,setAction]=useState("");
  const [environment,setEnvironment]=useState("production");
  const [result,setResult]=useState<any>();
  const [drift,setDrift]=useState<any>();
  const [assertions,setAssertions]=useState<any[]>([]);
  const [impacts,setImpacts]=useState<any[]>([]);
  const [checking,setChecking]=useState(false);
  const [error,setError]=useState("");

  function load(){api<any>(`/api/runbooks/${id}`).then(r=>{setItem(r);setAction(r.payload.steps[0]?.id||""); Promise.all([api<any[]>(`/api/projects/${r.project_id}/assertions`),api<any[]>(`/api/projects/${r.project_id}/change-impacts`)]).then(([nextAssertions,nextImpacts])=>{setAssertions(nextAssertions.filter(item=>item.affected_runbook_ids?.includes(r.id)));setImpacts(nextImpacts.filter(item=>item.impacts?.some((impact:any)=>impact.affected_runbook_ids?.includes(r.id))));}).catch(e=>setError(e.message));}).catch(e=>setError(e.message));}
  useEffect(()=>{load();},[id]);

  async function propose(){
    setError("");
    try{setResult(await api("/api/actions/propose",{method:"POST",body:JSON.stringify({project_id:item.project_id,runbook_id:id,action_id:action,params:{service_name:item.payload.services[0]||"service",environment}})}));}
    catch(requestError:any){setError(requestError.message);}
  }

  async function checkDrift(){
    setChecking(true);
    setError("");
    try{setDrift(await api(`/api/runbooks/${id}/drift?project_id=${item.project_id}`)); load();}
    catch(requestError:any){setError(requestError.message);}
    finally{setChecking(false);}
  }

  async function resolveAssertion(assertionId:string, actionName:string){
    const reason=actionName==="verify" ? "Verified against current evidence" : window.prompt("A rationale is required for this decision:");
    if(!reason?.trim())return;
    try{await api(`/api/assertions/${assertionId}/${actionName}`,{method:"POST",body:JSON.stringify({reason})});load();}
    catch(requestError:any){setError(requestError.message);}
  }

  if(error && !item)return <Page title="Runbook" description="Source-backed procedure"><div className="notice error">{error}</div></Page>;
  if(!item)return <Page title="Runbook" description="Loading source-backed procedure…"><div className="card empty">Loading…</div></Page>;
  const payload=item.payload;
  const driftStatus=drift?.drift_status||payload.drift_status||"unchecked";
  const reliabilityStatus=assertions.some(item=>["stale","contradicted"].includes(item.status))?"stale":assertions.some(item=>item.status==="possibly_stale")?"possibly stale":assertions.some(item=>item.status==="verified")?"verified against current evidence":assertions.length?"needs human verification":"unknown";
  const trust=payload.trust_score;
  return <Page title={item.name} description={item.description} action={<div className="row">
      <span className="badge info">v{payload.version||1}</span>
      <span className={`badge ${driftBadge[driftStatus]||""}`}>drift: {driftStatus.replace(/_/g," ")}</span>
      <span className={`badge ${reliabilityStatus.includes("stale")?"danger":reliabilityStatus.includes("verified")?"success":"warning"}`}>reliability: {reliabilityStatus}</span>
      <span className={`badge ${item.risk_level === "high" ? "danger" : "warning"}`}>{item.risk_level} risk · {Math.round(item.confidence*100)}%</span>
    </div>}>
    {error && <div className="notice error" style={{marginBottom:16}}>{error}</div>}
    <div className="grid two">
      <div className="stack">
        <section className="card">
          <div className="section-head"><h2>Procedure</h2><span className="badge">{payload.steps.length} steps</span></div>
          <div className="card-pad stack">{payload.steps.map((step:any,i:number)=><div className="source" key={step.id}><div className="row between"><strong>{i+1}. {step.description}</strong><span className={`badge ${step.approval_required?"warning":"success"}`}>{step.approval_required?"Approval":"Allowed"}</span></div>{step.command_template&&<pre className="trace">{step.command_template}</pre>}</div>)}</div>
        </section>
        <section className="card card-pad stack"><h2>Propose action</h2>
          <div className="row"><select value={action} onChange={e=>setAction(e.target.value)}>{payload.steps.map((s:any)=><option value={s.id} key={s.id}>{s.description}</option>)}</select><select style={{maxWidth:150}} value={environment} onChange={e=>setEnvironment(e.target.value)}><option>production</option><option>staging</option><option>development</option></select><button className="button" onClick={propose}>Evaluate</button></div>
          {result&&<div className={result.approval_required?"notice error":"notice"}><strong>{result.approval_required?"Approval required":"Action allowed"}</strong><br/>{result.reason}<br/><code>{result.command_preview||"No command template"}</code></div>}
        </section>
        <section className="card card-pad stack"><h2>Verification</h2>
          <div className="row">
            <button className="button secondary" disabled={checking} onClick={checkDrift}>{checking?"Checking sources…":"Check drift now"}</button>
            <Link className="button secondary" href="/simulation">Simulate this runbook →</Link>
          </div>
          {drift&&<div className="stack">{drift.signals.length?drift.signals.map((signal:any,index:number)=><div className="source" key={index}><div className="row between"><strong>{signal.type.replace(/_/g," ")}</strong><span className={`badge ${driftBadge[signal.severity]||""}`}>{signal.severity.replace(/_/g," ")}</span></div><p>{signal.detail}</p></div>):<div className="notice">All {drift.sources_checked} cited source(s) verified against current knowledge.</div>}</div>}
        </section>
        <section className="card"><div className="section-head"><h2>Active assertions</h2><span className="badge">{assertions.length}</span></div><div className="card-pad stack">{assertions.length?assertions.map(assertion=><div className="source" key={assertion.id}><div className="row between"><strong>{assertion.claim}</strong><span className={`badge ${driftBadge[assertion.status]||"warning"}`}>{assertion.status.replace(/_/g," ")}</span></div><p className="subtle">Owner: {assertion.verification_owner||"owner unknown"} · {assertion.environment_scope}</p><div className="row"><button className="button secondary" onClick={()=>resolveAssertion(assertion.id,"verify")}>Verify</button><button className="button secondary" onClick={()=>resolveAssertion(assertion.id,"mark-stale")}>Mark stale</button></div></div>):<p className="subtle">No assertion is linked to this runbook yet.</p>}</div></section>
      </div>
      <div className="stack">
        {trust&&<section className="card card-pad stack">
          <div className="row between"><h2>Trust score</h2><span className={`badge ${trust.level==="high"?"success":trust.level==="medium"?"warning":"danger"}`}>{trust.level} · {Math.round(trust.score*100)}%</span></div>
          <p className="subtle">{trust.reason}</p>
        </section>}
        <section className="card"><div className="section-head"><h2>Change impacts</h2><span className="badge">{impacts.length}</span></div><div className="card-pad stack">{impacts.length?impacts.map(impact=><Link className="source" href={`/reliability/${impact.id}`} key={impact.id}><strong>{impact.summary}</strong><p className="subtle">{impact.changed.files.join(", ")||"No connected file list"} · {impact.severity}</p></Link>):<p className="subtle">No connected code or configuration change impact has been recorded.</p>}</div></section>
        {payload.graph_trace?.length>0&&<section className="card card-pad stack"><h2>Graph trace</h2>{payload.graph_trace.slice(0,10).map((path:string)=><p className="subtle" key={path} style={{fontFamily:"ui-monospace, Menlo, monospace"}}>{path}</p>)}</section>}
        <section className="card"><div className="section-head"><h2>Source evidence</h2><span className="badge">{payload.sources.length}</span></div><div className="card-pad stack">{payload.sources.map((source:any)=><div className="source" key={source.title}><strong>{source.title}</strong><p>{source.snippet}</p>{source.url&&<a className="subtle" href={source.url}>Open source ↗</a>}</div>)}</div></section>
        {payload.versions?.length>0&&<section className="card"><div className="section-head"><h2>Versions</h2></div><div className="card-pad stack">{[...payload.versions].reverse().map((version:any)=><div className="row between" key={version.version}><span className="badge info">v{version.version}</span><span className="subtle">{formatDate(version.updated_at)} · confidence {Math.round((version.confidence||0)*100)}%</span></div>)}</div></section>}
        {payload.approval_rules?.length>0&&<section className="card card-pad stack"><h2>Approval policies</h2>{payload.approval_rules.map((rule:any,index:number)=><p className="subtle" key={index}>• {rule.action_type.replace(/_/g," ")} requires {rule.requires.replace(/_/g," ")}</p>)}</section>}
        <section className="card card-pad"><h2 style={{marginBottom:12}}>YAML</h2><pre className="yaml">{item.yaml}</pre></section>
      </div>
    </div>
  </Page>;
}
