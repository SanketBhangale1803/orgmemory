"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

const examples = [
  "@runbook why is reddit_service failing?",
  "@runbook how do we fix Kafka consumer timeouts?",
  "@runbook why did the Jenkins build fail?",
  "@runbook where should instagram_service store downloaded media?",
];

export default function Ask() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [query, setQuery] = useState(examples[0]);
  const [result, setResult] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    });
  }, []);

  async function ask() {
    setBusy(true);
    setError("");
    try {
      setResult(await api("/api/ask", {method:"POST", body:JSON.stringify({project_id:project, query})}));
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function extract() {
    setError("");
    try {
      const response: any = await api("/api/runbooks/extract", {method:"POST", body:JSON.stringify({project_id:project, query})});
      setError(response.runbooks_created ? `Generated ${response.runbooks[0].name}.` : response.reason);
    } catch (requestError: any) {
      setError(requestError.message);
    }
  }

  return <Page title="Ask Runbook" description="Answers are generated from retrieved evidence. Unsupported conclusions are withheld.">
    <section className="card card-pad stack">
      <div className="row">
        <select style={{maxWidth:260}} value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <input value={query} onChange={event=>setQuery(event.target.value)} onKeyDown={event=>{if(event.key === "Enter") ask();}}/>
        <button className="button" disabled={busy||!project||!query} onClick={ask}>{busy ? "Retrieving…" : "Ask"}</button>
      </div>
      <div className="row" style={{flexWrap:"wrap"}}>{examples.map(example=><button className="button secondary" key={example} onClick={()=>setQuery(example)}>{example.replace("@runbook ", "")}</button>)}</div>
    </section>
    {error && <div className={error.startsWith("Generated") ? "notice" : "notice error"} style={{marginTop:16}}>{error}</div>}
    {result && <div className="grid two" style={{marginTop:16}}>
      <div className="stack">
        <section className="card card-pad stack">
          <div className="row between"><h2>Grounded answer</h2><span className="badge info">HCAG routed</span></div>
          <p className="answer">{result.answer}</p>
          <div className="row between">
            <div className="row" style={{gap:28}}>
              <div><div className="subtle">Confidence</div><div className="confidence">{Math.round(result.confidence*100)}%</div></div>
              {result.trust_score && <div><div className="subtle">Trust</div><div className="row"><span className="confidence">{Math.round(result.trust_score.score*100)}%</span><span className={`badge ${result.trust_score.level === "high" ? "success" : result.trust_score.level === "medium" ? "warning" : "danger"}`}>{result.trust_score.level}</span></div></div>}
            </div>
            <button className="button" onClick={extract} disabled={!result.evidence.length} title={!result.evidence.length ? "A runbook requires supporting evidence" : "Extract an evidence-backed runbook"}>Extract runbook</button>
          </div>
          {result.trust_score?.reason && <p className="subtle">{result.trust_score.reason}</p>}
          {result.trust_score?.contradictions?.length > 0 && <div className="notice error"><strong>Conflicting evidence:</strong> {result.trust_score.contradictions.map((pair:any)=>`${pair.source_a} vs ${pair.source_b}`).join("; ")}</div>}
        </section>
        {result.change_correlation && <section className="card">
          <div className="section-head"><h2>Suspicious recent changes</h2><span className="badge warning">{result.change_correlation.suspects.length} suspect(s)</span></div>
          <div className="card-pad stack">{result.change_correlation.suspects.map((suspect:any)=><div className="source" key={suspect.item_id}>
            <div className="row between"><strong>{suspect.title}</strong><span className="badge">overlap {suspect.score}</span></div>
            <p>{suspect.reason}</p>
            {suspect.url && <a className="subtle" href={suspect.url}>Open change ↗</a>}
          </div>)}</div>
        </section>}
        <section className="card">
          <div className="section-head"><h2>Evidence</h2><span className="badge">{result.evidence.length} sources</span></div>
          <div className="card-pad stack">{result.evidence.length ? result.evidence.map((evidence:any)=><div className="source" key={evidence.chunk_id}><div className="row between"><strong>{evidence.source_title}</strong><span className="badge">{Math.round(evidence.confidence*100)}%</span></div><p>{evidence.snippet}</p>{evidence.source_url&&<a className="subtle" href={evidence.source_url}>Open source ↗</a>}</div>) : <div className="empty">No evidence met the grounding threshold.</div>}</div>
        </section>
      </div>
      <div className="stack">
        <section className="card card-pad"><h2>Likely cause</h2><p className="answer">{result.likely_cause}</p><div className="row" style={{flexWrap:"wrap"}}>{result.related_services.map((service:string)=><span className="badge info" key={service}>{service}</span>)}</div></section>
        {(result.related_files?.length || result.related_issues?.length || result.related_pull_requests?.length || result.related_slack_messages?.length) ? <section className="card card-pad stack"><h2>Related context</h2>
          {result.related_files?.length ? <div className="stack"><h3>Files</h3>{result.related_files.map((file:any)=>file.url ? <a className="subtle" style={{display:"block"}} key={file.title} href={file.url}>{file.title} ↗</a> : <p className="subtle" key={file.title}>{file.title}</p>)}</div> : null}
          {result.related_issues?.length ? <div className="stack"><h3>Issues</h3>{result.related_issues.map((issue:any)=>issue.url ? <a className="subtle" style={{display:"block"}} key={issue.title} href={issue.url}>{issue.title} ↗</a> : <p className="subtle" key={issue.title}>{issue.title}</p>)}</div> : null}
          {result.related_pull_requests?.length ? <div className="stack"><h3>Pull requests</h3>{result.related_pull_requests.map((pr:any)=>pr.url ? <a className="subtle" style={{display:"block"}} key={pr.title} href={pr.url}>{pr.title} ↗</a> : <p className="subtle" key={pr.title}>{pr.title}</p>)}</div> : null}
          {result.related_slack_messages?.length ? <div className="stack"><h3>Slack messages</h3>{result.related_slack_messages.map((message:any)=>message.url ? <a className="subtle" style={{display:"block"}} key={message.title} href={message.url}>{message.title} ↗</a> : <p className="subtle" key={message.title}>{message.title}</p>)}</div> : null}
        </section> : null}
        <section className="card card-pad stack"><h2>Action boundary</h2><div><h3>Safe actions</h3>{result.safe_actions.length ? result.safe_actions.map((action:string)=><p className="subtle" key={action}>✓ {action}</p>) : <p className="subtle">No evidence-backed safe actions found.</p>}</div><div><h3>Approval required</h3>{result.approval_required.length ? result.approval_required.map((action:string)=><p className="subtle" key={action}>• {action}</p>) : <p className="subtle">No risky actions extracted.</p>}</div></section>
        <section className="card card-pad stack"><h2>Graph trace</h2>
          {result.retrieval_trace?.graph_path_explanations?.length ? result.retrieval_trace.graph_path_explanations.map((path:string)=><p className="subtle" key={path} style={{fontFamily:"ui-monospace, Menlo, monospace"}}>{path}</p>) : <p className="subtle">No graph paths were traversed for this answer.</p>}
        </section>
        <section className="card card-pad"><h2 style={{marginBottom:12}}>HCAG retrieval trace</h2><pre className="trace">{JSON.stringify(result.retrieval_trace,null,2)}</pre></section>
      </div>
    </div>}
  </Page>;
}
