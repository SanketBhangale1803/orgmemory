"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Simulation() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [runbooks, setRunbooks] = useState<any[]>([]);
  const [runbook, setRunbook] = useState("");
  const [scenario, setScenario] = useState("Simulate Kafka outage for reddit_service");
  const [environment, setEnvironment] = useState("production");
  const [result, setResult] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    }).catch(e => setError(e.message));
  }, []);

  useEffect(() => {
    if (!project) return;
    api<any[]>(`/api/runbooks?project_id=${project}`).then(items => {
      setRunbooks(items);
      setRunbook("");
    }).catch(()=>setRunbooks([]));
  }, [project]);

  async function simulate() {
    setBusy(true);
    setError("");
    try {
      setResult(await api("/api/simulate", {method:"POST", body:JSON.stringify({
        project_id: project,
        runbook_id: runbook || null,
        scenario: runbook ? "" : scenario,
        environment,
      })}));
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return <Page title="Simulation" description="Dry-run a runbook through the same AgentGate policy used for live proposals. Nothing executes; every step reports its decision, approvals, and missing context.">
    <section className="card card-pad stack">
      <div className="row">
        <select style={{maxWidth:240}} value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select style={{maxWidth:300}} value={runbook} onChange={event=>setRunbook(event.target.value)}>
          <option value="">Select runbook from scenario…</option>
          {runbooks.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <select style={{maxWidth:150}} value={environment} onChange={event=>setEnvironment(event.target.value)}><option>production</option><option>staging</option><option>development</option></select>
      </div>
      <div className="row">
        <input value={scenario} disabled={!!runbook} onChange={event=>setScenario(event.target.value)} placeholder="Describe the scenario, e.g. Simulate Kafka outage for reddit_service"/>
        <button className="button" disabled={busy||!project||(!runbook&&!scenario)} onClick={simulate}>{busy ? "Simulating…" : "Simulate"}</button>
      </div>
    </section>
    {error && <div className="notice error" style={{marginTop:16}}>{error}</div>}
    {result && (result.applicable_runbook ? <div className="grid two" style={{marginTop:16}}>
      <div className="stack">
        <section className="card card-pad stack">
          <div className="row between"><h2>{result.applicable_runbook.name}</h2><span className={`badge ${result.verdict === "blocked_without_approvals" ? "warning" : "success"}`}>{result.verdict.replace(/_/g," ")}</span></div>
          <p className="subtle">{result.selection_reason}</p>
          <div className="row">
            <span className="badge info">v{result.applicable_runbook.version}</span>
            <span className="badge">{result.applicable_runbook.risk_level} risk</span>
            <span className="badge">drift: {result.applicable_runbook.drift_status}</span>
            <span className="badge">policy: {result.policy_engine}</span>
          </div>
        </section>
        <section className="card">
          <div className="section-head"><h2>Step walkthrough</h2><span className="badge">{result.steps.length} steps</span></div>
          <div className="card-pad stack">{result.steps.map((step:any)=><div className="source" key={step.step_id}>
            <div className="row between"><strong>{step.description}</strong><span className={`badge ${step.approval_required?"warning":"success"}`}>{step.approval_required?`Approval: ${step.approval_role}`:"Allowed"}</span></div>
            <p className="subtle">{step.action_type} · risk {step.risk_score} · {step.policy_reason}</p>
            {step.command_preview && <pre className="trace">{step.command_preview}</pre>}
            {step.unresolved_params.length > 0 && <p className="subtle">Missing parameters: {step.unresolved_params.join(", ")}</p>}
          </div>)}</div>
        </section>
      </div>
      <div className="stack">
        <section className="card card-pad stack"><h2>Before an agent may execute</h2>
          {result.evidence_needed_before_execution.length ? result.evidence_needed_before_execution.map((line:string)=><p className="subtle" key={line}>• {line}</p>) : <p className="subtle">No additional context required.</p>}
        </section>
        <section className="card card-pad stack"><h2>Gates</h2>
          <div><h3>Approvals required</h3>{result.approvals_required.length ? result.approvals_required.map((id:string)=><p className="subtle" key={id}>• {id}</p>) : <p className="subtle">None</p>}</div>
          <div><h3>Dangerous steps</h3>{result.dangerous_steps.length ? result.dangerous_steps.map((id:string)=><p className="subtle" key={id}>• {id}</p>) : <p className="subtle">None</p>}</div>
        </section>
        <section className="card"><div className="section-head"><h2>Backing evidence</h2><span className="badge">{result.sources.length} sources</span></div>
          <div className="card-pad stack">{result.sources.map((source:any)=><div className="source" key={source.title}><strong>{source.title}</strong><p>{source.snippet}</p></div>)}</div>
        </section>
      </div>
    </div> : <div className="notice" style={{marginTop:16}}><strong>No applicable runbook.</strong><br/>{result.reason}</div>)}
    {!result && !error && <div className="card empty" style={{marginTop:16}}>Pick a runbook or describe a scenario. The simulation walks each step through policy so you can see what an agent would be allowed to do before granting it anything.</div>}
  </Page>;
}
