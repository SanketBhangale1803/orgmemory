"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const statusBadge: Record<string, string> = {
  fresh: "success",
  possibly_stale: "warning",
  needs_human_review: "warning",
  conflicting_evidence: "danger",
  stale: "danger",
};

export default function Drift() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [report, setReport] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    }).catch(e => setError(e.message));
  }, []);

  async function check() {
    setBusy(true);
    setError("");
    try {
      setReport(await api(`/api/projects/${project}/drift`));
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return <Page title="Runbook Drift" description="Compare every extracted runbook against the knowledge that exists now. Drift is detected from real source changes, never assumed.">
    <section className="card card-pad">
      <div className="row">
        <select style={{maxWidth:280}} value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <button className="button" disabled={busy||!project} onClick={check}>{busy ? "Checking sources…" : "Run drift check"}</button>
      </div>
    </section>
    {error && <div className="notice error" style={{marginTop:16}}>{error}</div>}
    {report && (report.results.length ? <div className="stack" style={{marginTop:16}}>
      <section className="card card-pad row between">
        <div><div className="subtle">Runbooks checked</div><div className="confidence">{report.runbooks_checked}</div></div>
        <div><div className="subtle">Stale</div><div className="confidence">{report.stale}</div></div>
      </section>
      {report.results.map((item:any)=><section className="card" key={item.runbook_id}>
        <div className="section-head"><h2>{item.runbook_key}</h2><span className={`badge ${statusBadge[item.drift_status]||"info"}`}>{item.drift_status.replace(/_/g," ")}</span></div>
        <div className="card-pad stack">
          <p className="subtle">{item.sources_checked} cited source(s) checked at {formatDate(item.checked_at)}</p>
          {item.signals.length ? item.signals.map((signal:any,index:number)=><div className="source" key={index}>
            <div className="row between"><strong>{signal.type.replace(/_/g," ")}</strong><span className={`badge ${statusBadge[signal.severity]||"info"}`}>{signal.severity.replace(/_/g," ")}</span></div>
            <p>{signal.detail}</p>
          </div>) : <div className="empty">No drift signals. Cited sources are unchanged and services still exist in the graph.</div>}
        </div>
      </section>)}
    </div> : <div className="card empty" style={{marginTop:16}}>This project has no extracted runbooks yet. Extract one from Ask Runbook, then check its drift here.</div>)}
    {!report && !error && <div className="card empty" style={{marginTop:16}}>Select a project and run a drift check to see which runbooks are still backed by current knowledge.</div>}
  </Page>;
}
