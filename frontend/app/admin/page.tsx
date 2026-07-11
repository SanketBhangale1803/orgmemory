"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Admin() {
  const [runtime, setRuntime] = useState<any>();
  const [importers, setImporters] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [memories, setMemories] = useState<any[]>();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    api("/api/settings/runtime").then(setRuntime).catch(e => setError(e.message));
    api<any[]>("/api/importers").then(setImporters).catch(()=>setImporters([]));
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    }).catch(()=>setProjects([]));
  }, []);

  useEffect(() => {
    if (!project) return;
    api<any[]>(`/api/projects/${project}/memories`).then(setMemories).catch(()=>setMemories([]));
  }, [project]);

  async function derive() {
    setError("");
    setNotice("");
    try {
      const result: any = await api(`/api/projects/${project}/memories/derive`, {method:"POST"});
      setNotice(result.candidates_created ? `Derived ${result.candidates_created} candidate(s) from ingested evidence.` : "No new operational rules found in ingested evidence.");
      setMemories(await api(`/api/projects/${project}/memories`));
    } catch (requestError: any) {
      setError(requestError.message);
    }
  }

  async function resolve(id: string, approve: boolean) {
    setError("");
    try {
      await api(`/api/memories/${id}/${approve ? "approve" : "reject"}`, {method:"POST", body:JSON.stringify({resolved_by:"admin"})});
      setMemories(await api(`/api/projects/${project}/memories`));
    } catch (requestError: any) {
      setError(requestError.message);
    }
  }

  const security = runtime ? [
    ["Environment", runtime.environment],
    ["Auth dev mode", String(runtime.auth_dev_mode)],
    ["Local command execution", String(runtime.allow_local_command_execution)],
    ["Graph backend", runtime.graph_backend],
    ["GitHub OAuth configured", String(runtime.github_oauth_configured)],
    ["Slack OAuth configured", String(runtime.slack_oauth_configured)],
  ] : [];

  return <Page title="Admin & Security" description="Runtime security posture, incident-tool migration, and the operational memory review queue.">
    {error && <div className="notice error" style={{marginBottom:16}}>{error}</div>}
    <div className="grid two">
      <div className="stack">
        <section className="card">
          <div className="section-head"><h2>Security posture</h2>{runtime && <span className={`badge ${runtime.allow_local_command_execution ? "danger" : "success"}`}>{runtime.allow_local_command_execution ? "Execution enabled" : "Execution disabled"}</span>}</div>
          {!runtime ? <div className="empty">Loading…</div> : <table className="table"><tbody>
            {security.map(([label, value]) => <tr key={label}><td>{label}</td><td><code>{value}</code></td></tr>)}
          </tbody></table>}
        </section>
        <section className="card">
          <div className="section-head"><h2>Migrate from incident tools</h2><span className="badge">{importers.filter(item=>item.status==="connected").length} connected</span></div>
          <div className="card-pad stack">
            {importers.length === 0 && <div className="empty">Loading importer registry…</div>}
            {importers.map(importer => <div className="source row between" key={importer.name}>
              <div><strong>Import from {importer.label}</strong><p>{importer.implemented ? "Live API importer" : "Interface scaffolded — live client planned"} · set <code>{importer.token_env}</code></p></div>
              <span className={`badge ${importer.status === "connected" ? "success" : ""}`}>{importer.status === "connected" ? "Connected" : "Not connected"}</span>
            </div>)}
          </div>
        </section>
      </div>
      <div className="stack">
        <section className="card">
          <div className="section-head"><h2>Operational memory</h2>
            <div className="row">
              <select style={{maxWidth:200}} value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option key={item.id} value={item.id}>{item.name}</option>)}</select>
              <button className="button secondary" disabled={!project} onClick={derive}>Derive from evidence</button>
            </div>
          </div>
          <div className="card-pad stack">
            {notice && <div className="notice">{notice}</div>}
            {!memories && <div className="empty">Loading…</div>}
            {memories && !memories.length && <div className="empty">No operational memories yet. Derive candidates from ingested evidence — every memory cites its source and requires approval before it counts.</div>}
            {memories?.map(memory => <div className="source" key={memory.id}>
              <div className="row between"><strong>{memory.statement}</strong><span className={`badge ${memory.status === "approved" ? "success" : memory.status === "rejected" ? "danger" : "warning"}`}>{memory.status}</span></div>
              <p>{memory.memory_type.replace(/_/g," ")} · source: {memory.evidence[0]?.source_title}</p>
              {memory.status === "proposed" && <div className="row" style={{marginTop:10}}>
                <button className="button" onClick={()=>resolve(memory.id, true)}>Approve</button>
                <button className="button danger" onClick={()=>resolve(memory.id, false)}>Reject</button>
              </div>}
            </div>)}
          </div>
        </section>
      </div>
    </div>
  </Page>;
}
