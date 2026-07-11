"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import { api } from "@/lib/api";

export default function Ingest() {
  const [projects, setProjects] = useState<any[]>([]);
  const [repositories, setRepositories] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [repo, setRepo] = useState("");
  const [name, setName] = useState("");
  const [project, setProject] = useState("");
  const [channel, setChannel] = useState("");
  const [sourceType, setSourceType] = useState("incident");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<any[]>("/api/projects").then(items => { setProjects(items); if (items[0]) setProject(items[0].id); });
    api<any[]>("/api/connectors/github/repos").then(setRepositories).catch(() => undefined);
    api<any[]>("/api/connectors/slack/channels").then(items => { setChannels(items); if (items[0]) setChannel(items[0].id); }).catch(() => undefined);
  }, []);

  async function ingestRepo() {
    setBusy(true); setStatus("");
    try {
      const result: any = await api("/api/ingest/github", {method:"POST", body:JSON.stringify({repo_url_or_path:repo, project_name:name})});
      setStatus(`Scanned ${result.files_scanned} files, ${result.issues_scanned} issues, and created ${result.knowledge_chunks_created} knowledge chunks.`);
    } catch (error: any) { setStatus(error.message); } finally { setBusy(false); }
  }

  async function upload() {
    setBusy(true); setStatus("");
    try {
      const result: any = await api("/api/ingest/upload", {method:"POST", body:JSON.stringify({project_id:project, source_type:sourceType, title, content})});
      setStatus(`Ingested ${result.chunks_created} evidence chunks.`); setTitle(""); setContent("");
    } catch (error: any) { setStatus(error.message); } finally { setBusy(false); }
  }

  async function ingestSlack() {
    setBusy(true); setStatus("");
    try {
      const result: any = await api("/api/ingest/slack", {method:"POST", body:JSON.stringify({project_id:project, channel_id:channel, limit:200})});
      setStatus(`Ingested ${result.messages_scanned} Slack messages from #${result.channel}.`);
    } catch (error: any) { setStatus(error.message); } finally { setBusy(false); }
  }

  const success = status.startsWith("Scanned") || status.startsWith("Ingested");
  return <Page title="Ingest knowledge" description="Index repositories and operational artifacts into ArcadeDB graph memory.">
    {status && <div className={success ? "notice" : "notice error"}>{status}</div>}
    <div className="grid two" style={{marginTop:status ? 16 : 0}}>
      <section className="card card-pad stack">
        <div><h2>Repository</h2><p className="subtle">Connected GitHub accounts include private repositories, issues, and pull requests. Local paths are also supported.</p></div>
        {repositories.length > 0 && <div className="field"><label>Accessible GitHub repositories</label><select value={repo} onChange={event => { const selected = repositories.find(item => item.clone_url === event.target.value); setRepo(event.target.value); if (selected && !name) setName(selected.name); }}><option value="">Choose a repository</option>{repositories.map(item => <option key={item.id} value={item.clone_url}>{item.full_name}{item.private ? " · private" : ""}</option>)}</select></div>}
        <div className="field"><label>Repository URL or local path</label><input value={repo} onChange={event=>setRepo(event.target.value)} placeholder="https://github.com/company/service or ~/code/service"/></div>
        <div className="field"><label>Project name</label><input value={name} onChange={event=>setName(event.target.value)} placeholder="Payments platform"/></div>
        <button className="button" onClick={ingestRepo} disabled={busy||!repo||!name}>{busy ? "Scanning repository…" : "Ingest repository"}</button>
      </section>
      <section className="card card-pad stack">
        <div><h2>Operational knowledge</h2><p className="subtle">Paste incidents, Slack exports, logs, docs, tickets, or support context.</p></div>
        <div className="row"><div className="field" style={{flex:1}}><label>Project</label><select value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></div><div className="field" style={{flex:1}}><label>Type</label><select value={sourceType} onChange={event=>setSourceType(event.target.value)}>{["incident","slack_export","log","doc","support_ticket","gmail_export","clickup_ticket","other"].map(value=><option key={value}>{value}</option>)}</select></div></div>
        <div className="field"><label>Source title</label><input value={title} onChange={event=>setTitle(event.target.value)} placeholder="June Kafka incident"/></div>
        <div className="field"><label>Content</label><textarea value={content} onChange={event=>setContent(event.target.value)} placeholder="Paste source content exactly as it appeared…"/></div>
        <button className="button" onClick={upload} disabled={busy||!project||!title||!content}>Ingest knowledge</button>
      </section>
      <section className="card card-pad stack" style={{gridColumn:"1 / -1"}}>
        <div className="row between"><div><h2>Slack channel history</h2><p className="subtle">Ingest messages and threads from a connected workspace with timestamps and permalinks.</p></div>{channels.length === 0 && <span className="badge warning">Connect Slack first</span>}</div>
        <div className="row"><select value={project} onChange={event=>setProject(event.target.value)}>{projects.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select><select value={channel} onChange={event=>setChannel(event.target.value)} disabled={!channels.length}>{channels.length ? channels.map(item=><option value={item.id} key={item.id}>#{item.name}{item.is_private ? " · private" : ""}</option>) : <option>No accessible channels</option>}</select><button className="button" onClick={ingestSlack} disabled={busy||!project||!channel}>Ingest channel</button></div>
      </section>
    </div>
  </Page>;
}
