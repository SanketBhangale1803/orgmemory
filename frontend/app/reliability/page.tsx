"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api, formatDate } from "@/lib/api";

const tone: Record<string, string> = { verified: "success", proposed: "warning", possibly_stale: "warning", stale: "danger", contradicted: "danger", critical: "danger", high: "danger", medium: "warning" };

export default function Reliability() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [impacts, setImpacts] = useState<any[]>([]);
  const [assertions, setAssertions] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [selectedAssertions, setSelectedAssertions] = useState<string[]>([]);

  useEffect(() => { api<any[]>("/api/projects").then(items => { setProjects(items); if (items[0]) setProject(items[0].id); }).catch(error => setError(error.message)); }, []);
  useEffect(() => { if (project) load(); }, [project]);
  async function load() {
    try { const [nextImpacts, nextAssertions] = await Promise.all([api<any[]>(`/api/projects/${project}/change-impacts`), api<any[]>(`/api/projects/${project}/assertions`)]); setImpacts(nextImpacts); setAssertions(nextAssertions); setSelectedAssertions([]); }
    catch (requestError: any) { setError(requestError.message); }
  }
  async function analyze() {
    const selected = projects.find(item => item.id === project);
    if (!selected?.repository) { setError("This project has no connected repository. Re-ingest it from the Ingest page before checking for source changes."); return; }
    setBusy(true); setError(""); setMessage("");
    try { const result:any = await api("/api/ingest/github", { method: "POST", body: JSON.stringify({ repo_url_or_path: selected.repository, project_name: selected.name }) }); const changed = result.change?.changed_files?.length || 0; setMessage(changed ? `Re-indexed repository and analyzed ${changed} changed file${changed === 1 ? "" : "s"}.` : "Repository is current: no changed files were detected against the last ingestion."); await load(); }
    catch (requestError: any) { setError(requestError.message); }
    finally { setBusy(false); }
  }
  async function bulkReview(action:"verify"|"dismiss", ids = selectedAssertions) {
    if (!ids.length) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const reason = action === "verify" ? "Bulk review approved against current cited evidence." : "Bulk review dismissed as not operationally applicable.";
      const result:any = await api(`/api/projects/${project}/assertions/bulk-review`, {method:"POST", body:JSON.stringify({assertion_ids:ids, action, reason})});
      setMessage(`${result.reviewed} assertion${result.reviewed === 1 ? "" : "s"} ${action === "verify" ? "verified" : "dismissed"}.`);
      await load();
    } catch (requestError:any) { setError(requestError.message); }
    finally { setBusy(false); }
  }
  const unresolved = assertions.filter(item => ["proposed", "possibly_stale", "stale", "contradicted"].includes(item.status) && item.policy_status !== "dismissed");
  const proposed = unresolved.filter(item => item.status === "proposed");
  const connectedImpacts = impacts.filter(item => item.changed.files.length || item.changed.source_evidence.length);
  return <Page title="Runbook Reliability" description="CI/CD for production runbooks: review the evidence when code or configuration changes may make a procedure stale." action={<div className="row"><select value={project} onChange={event => setProject(event.target.value)}>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select><button className="button secondary" onClick={analyze} disabled={!project || busy}>{busy ? "Refreshing…" : "Refresh repository"}</button></div>}>
    {error && <div className="notice error">{error}</div>}
    {message && <div className="notice">{message}</div>}
    <section className="grid three" style={{marginBottom:16}}><div className="card card-pad"><div className="subtle">Open change impacts</div><div className="confidence">{connectedImpacts.filter(item => item.status === "action_required").length}</div></div><div className="card card-pad"><div className="subtle">Assertions needing review</div><div className="confidence">{unresolved.length}</div></div><div className="card card-pad"><div className="subtle">Observability</div><p className="subtle">Not connected · conclusions use code/config evidence only.</p></div></section>
    {!project ? <div className="card empty">No project is available. Ingest a repository before reviewing runbook reliability.</div> : connectedImpacts.length ? <section className="stack">{connectedImpacts.map(impact => <Link className="card" href={`/reliability/${impact.id}`} key={impact.id}><div className="section-head"><div><h2>{impact.summary}</h2><p className="subtle">{impact.change_type.replace(/_/g," ")} · {impact.change_ref} · {formatDate(impact.created_at)}</p></div><span className={`badge ${tone[impact.severity] || "info"}`}>{impact.severity}</span></div><div className="card-pad row between"><span>{impact.changed.files.length} changed file(s) · {impact.impacts.length} linked assertion(s)</span><span className={`badge ${impact.status === "action_required" ? "warning" : "success"}`}>{impact.status.replace(/_/g," ")}</span></div></Link>)}</section> : <div className="card empty">No connected repository changes have been detected. Select <strong>Refresh repository</strong> after a GitHub/local-repository change to re-index and compare it with the last ingestion.</div>}
    <section className="card assertion-review" style={{marginTop:16}}><div className="section-head"><div><h2>Operational assertions</h2><p className="subtle">Review evidence-backed claims in one governed batch.</p></div><span className="badge">{assertions.length}</span></div>{unresolved.length > 0 && <div className="bulk-review-bar"><label><input type="checkbox" checked={selectedAssertions.length === unresolved.length} onChange={event=>setSelectedAssertions(event.target.checked ? unresolved.map(item=>item.id) : [])}/> Select all needing review</label><div className="row"><button className="button secondary" disabled={busy || !selectedAssertions.length} onClick={()=>bulkReview("dismiss")}>Dismiss selected</button><button className="button" disabled={busy || !proposed.length} onClick={()=>bulkReview("verify", proposed.map(item=>item.id))}>Approve all proposed</button></div></div>}<div className="card-pad stack">{assertions.length ? assertions.slice(0,40).map(assertion => <label className={`source assertion-row ${selectedAssertions.includes(assertion.id) ? "selected" : ""}`} key={assertion.id}><input type="checkbox" checked={selectedAssertions.includes(assertion.id)} disabled={assertion.status === "verified" || assertion.policy_status === "dismissed"} onChange={event=>setSelectedAssertions(current=>event.target.checked ? [...current, assertion.id] : current.filter(id=>id !== assertion.id))}/><div><div className="row between"><strong>{assertion.title}</strong><span className={`badge ${tone[assertion.status] || "info"}`}>{assertion.policy_status === "dismissed" ? "dismissed" : assertion.status.replace(/_/g," ")}</span></div><p>{assertion.claim}</p><span className="subtle">Reviewer: {assertion.verification_owner} · {assertion.environment_scope}</span><small>{assertion.verification_reason}</small></div></label>) : <p className="subtle">Assertions are created when a runbook is extracted from cited evidence.</p>}</div></section>
  </Page>;
}
