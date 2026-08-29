"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import Page from "@/components/Page";
import GitHubIcon from "@/components/icons/GitHubIcon";
import { api } from "@/lib/api";

type SourceKind = "paste" | "github" | "slack";

const sourceChoices = [
  {id: "paste", icon: "✦", title: "Paste knowledge", note: "Fastest", description: "A decision, policy, report, or any useful context."},
  {id: "github", icon: "github", title: "Connect a repository", note: "Automatic", description: "Code, docs, issues, pull requests, and ownership."},
  {id: "slack", icon: "SL", title: "Remember a channel", note: "Continuous", description: "Team decisions, conventions, and conversations."},
] as const;

export default function Ingest() {
  const [kind, setKind] = useState<SourceKind>("paste");
  const [projects, setProjects] = useState<any[]>([]);
  const [repositories, setRepositories] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [catalog, setCatalog] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [project, setProject] = useState("__new__");
  const [newProject, setNewProject] = useState("Company memory");
  const [team, setTeam] = useState("");
  const [repo, setRepo] = useState("");
  const [repoName, setRepoName] = useState("");
  const [channel, setChannel] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState("doc");
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState(0);
  const [error, setError] = useState("");
  const [result, setResult] = useState<any>();
  /* Indexing every repository at once is the normal first move after
     connecting GitHub, so it belongs beside the one-repository picker rather
     than only in the API. */
  const [bulk, setBulk] = useState<{ queued: number } | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    });
    api<any[]>("/api/connectors").then(setConnections);
    api<any[]>("/api/connectors/catalog").then(setCatalog).catch(() => undefined);
    api<{result?: {repositories?: any[]}}>("/api/connectors/github/tools/list_repositories", {
      method: "POST",
      body: JSON.stringify({arguments: {}}),
    }).then(response => setRepositories(response.result?.repositories || [])).catch(() => undefined);
    api<any[]>("/api/connectors/slack/channels").then(items => {
      setChannels(items);
      if (items[0]) setChannel(items[0].id);
    }).catch(() => undefined);
    api<any>("/api/auth/me")
      .then(me => api<any[]>(`/api/workspaces/${me.active_workspace_id}/teams`))
      .then(setTeams).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!busy) { setPhase(0); return; }
    const timer = window.setInterval(() => setPhase(value => Math.min(value + 1, 2)), 850);
    return () => window.clearInterval(timer);
  }, [busy]);

  const connected = (provider: string) => connections.some(item => item.provider === provider && item.connected);
  const selectedRepo = useMemo(() => repositories.find(item => item.clone_url === repo), [repositories, repo]);

  async function ensureProject() {
    if (project !== "__new__") return project;
    const created: any = await api("/api/projects", {
      method: "POST",
      body: JSON.stringify({name: newProject.trim() || "Company memory", team_ids: team ? [team] : []}),
    });
    setProjects(items => [created, ...items]);
    setProject(created.id);
    return created.id;
  }

  async function buildMemory() {
    setBusy(true);
    setError("");
    setResult(undefined);
    try {
      const team_ids = team ? [team] : [];
      let response: any;
      if (kind === "github") {
        response = await api("/api/ingest/github", {
          method: "POST",
          body: JSON.stringify({repo_url_or_path: repo, project_name: repoName || selectedRepo?.full_name || selectedRepo?.name, team_ids}),
        });
      } else if (kind === "slack") {
        const projectId = await ensureProject();
        response = await api("/api/ingest/slack", {
          method: "POST",
          body: JSON.stringify({project_id: projectId, channel_id: channel, limit: 200, team_ids}),
        });
      } else {
        const projectId = await ensureProject();
        response = await api("/api/ingest/upload", {
          method: "POST",
          body: JSON.stringify({project_id: projectId, source_type: sourceType, title: title.trim() || "Company knowledge", content, team_ids, artifact_type: sourceType === "report" ? "report" : ""}),
        });
      }
      setPhase(2);
      setResult(response);
    } catch (exc: any) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  async function indexEverything() {
    setBulkBusy(true);
    setError("");
    try {
      const response = await api<{ repositories_queued: number }>("/api/ingest/github/all", {
        method: "POST",
        body: JSON.stringify({ include_archived: false }),
      });
      setBulk({ queued: response.repositories_queued });
    } catch (cause: any) {
      setError(cause.message);
    } finally {
      setBulkBusy(false);
    }
  }

  const canBuild = kind === "paste" ? Boolean(content.trim() && (project !== "__new__" || newProject.trim())) : kind === "github" ? Boolean(repo && (repoName || selectedRepo)) : Boolean(channel && (project !== "__new__" || newProject.trim()));
  const memoryCount = result?.memory_units_created ?? result?.memory_unit_ids?.length ?? 0;

  return <Page eyebrow="Build company memory" title="Add knowledge" description="Choose a source. OrgMemory handles chunking, memory extraction, relationships, and indexing automatically.">
    <section className="memory-builder">
      <div className="builder-progress" aria-label="Memory creation progress">
        <span className="active"><i>1</i>Choose</span><b/><span className={busy || result ? "active" : ""}><i>2</i>Remember</span><b/><span className={result ? "active" : ""}><i>3</i>Ask</span>
      </div>

      {!result ? <>
        <div className="source-choice-grid">
          {sourceChoices.map(choice => <button key={choice.id} className={`source-choice ${kind === choice.id ? "selected" : ""}`} onClick={() => {setKind(choice.id);setError("");}}>
            <span className="source-choice-icon">{choice.icon === "github" ? <GitHubIcon size={24}/> : choice.icon}</span>
            <span><small>{choice.note}</small><strong>{choice.title}</strong><p>{choice.description}</p></span>
            <i className="choice-check">✓</i>
          </button>)}
        </div>

        <div className="ingest-ecosystem-strip">
          <div><strong>Company-wide source map</strong><span>Live sources can be selected above. Upcoming adapters remain visible without pretending they are connected.</span></div>
          <div>{catalog.filter(item => item.role !== "delivery").map(item => <span key={item.provider} className={item.status}><i>{item.label.split(/\s+/).map((part:string)=>part[0]).join("").slice(0,2)}</i>{item.label}<em>{item.status === "live" ? "live" : item.status === "next" ? "next" : "planned"}</em></span>)}</div>
          <Link href="/connectors">Manage connections →</Link>
        </div>

        <div className="builder-card">
          {kind === "paste" && <div className="quick-memory-form">
            <div className="builder-title"><span className="spark-orbit"><i/><i/><i/></span><div><h2>What should your company remember?</h2><p>Paste it as written. Only confident, source-backed statements become memory.</p></div></div>
            <textarea autoFocus aria-label="Company knowledge" value={content} onChange={event => setContent(event.target.value)} placeholder="Paste a real decision, policy, ownership note, project brief, or report from your company…" />
            <input aria-label="Source title" value={title} onChange={event => setTitle(event.target.value)} placeholder="Optional source title" />
          </div>}

          {kind === "github" && <div className="quick-memory-form">
            <div className="builder-title"><span className="source-hero-icon"><GitHubIcon size={27}/></span><div><h2>Choose a repository</h2><p>OrgMemory reads the repository and builds its project memory automatically.</p></div></div>
            {!connected("github") ? <div className="builder-connect"><strong>Connect GitHub once</strong><p>Authorize the repositories you want OrgMemory to remember.</p><Link className="button" href="/connectors">Connect GitHub →</Link></div> : <><select aria-label="GitHub repository" value={repo} onChange={event => {setRepo(event.target.value);const match=repositories.find(item=>item.clone_url===event.target.value);setRepoName(match?.full_name || match?.name || "");}}><option value="">Select a repository…</option>{repositories.map(item => <option key={item.id} value={item.clone_url}>{item.full_name}{item.private ? " · Private" : ""}</option>)}</select><p className="privacy-note"><i/> Private repositories supported. Existing source permissions are preserved.</p>
              <div className="bulk-index">
                <div>
                  <strong>Or index everything you have access to</strong>
                  <span>
                    {bulk
                      ? `${bulk.queued} repositor${bulk.queued === 1 ? "y" : "ies"} queued. Each becomes its own memory space as it finishes.`
                      : `${repositories.length} repositor${repositories.length === 1 ? "y" : "ies"} visible to this workspace's GitHub grant.`}
                  </span>
                </div>
                <button className="button secondary" disabled={bulkBusy || !repositories.length} onClick={indexEverything}>
                  {bulkBusy ? "Queueing…" : bulk ? "Queue again" : "Index all repositories"}
                </button>
              </div></>}
          </div>}

          {kind === "slack" && <div className="quick-memory-form">
            <div className="builder-title"><span className="source-hero-icon slack">SL</span><div><h2>Choose a Slack channel</h2><p>Remember team decisions and conventions with links back to each message.</p></div></div>
            {!connected("slack") ? <div className="builder-connect"><strong>Connect Slack once</strong><p>Choose which channels OrgMemory may read.</p><Link className="button" href="/connectors">Connect Slack →</Link></div> : <select aria-label="Slack channel" value={channel} onChange={event => setChannel(event.target.value)}>{channels.map(item => <option key={item.id} value={item.id}>#{item.name}{item.is_private ? " · Private" : ""}</option>)}</select>}
          </div>}

          {kind !== "github" && <div className="builder-project-row"><label>Save to</label><select value={project} onChange={event => setProject(event.target.value)}><option value="__new__">New memory space</option>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>{project === "__new__" && <input aria-label="New memory space name" value={newProject} onChange={event => setNewProject(event.target.value)} />}</div>}

          <details className="builder-options"><summary>Options <span>Team visibility and source type</span></summary><div>{teams.length ? <div className="field"><label>Visible to</label><select value={team} onChange={event => setTeam(event.target.value)}><option value="">Everyone in this workspace</option>{teams.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div> : null}{kind === "paste" && <div className="field"><label>Source type</label><select value={sourceType} onChange={event => setSourceType(event.target.value)}>{["doc","report","slack_export","incident","log","text"].map(value => <option key={value}>{value.replace(/_/g," ")}</option>)}</select></div>}</div></details>

          {error && <div className="notice error">{error}</div>}
          {busy ? <div className="memory-building"><div className="memory-pulse"><i/><i/><i/></div><div><strong>{["Reading the source…","Extracting atomic memory…","Linking the memory graph…"][phase]}</strong><span>Source → chunks → memory → relationships</span></div></div> : <button className="button builder-submit" disabled={!canBuild} onClick={buildMemory}>{kind === "paste" ? "Remember this" : kind === "github" ? "Build repository memory" : "Remember this channel"}<span>→</span></button>}
        </div>
      </> : <section className="memory-success">
        <div className="success-rings"><i/><i/><i/><span>✓</span></div>
        <span className="panel-label">Memory is ready</span>
        <h2>OrgMemory learned from this source.</h2>
        <p>{memoryCount} atomic memories and {result.chunks_created ?? result.knowledge_chunks_created ?? 0} evidence chunks are now available to your agents.</p>
        <div className="success-stats"><div><strong>{memoryCount}</strong><span>Memories</span></div><div><strong>{result.source_revision?.version || 1}</strong><span>Source version</span></div><div><strong>{result.change_set?.conflicts?.length || 0}</strong><span>Conflicts</span></div></div>
        <div className="success-actions"><Link className="button" href="/workspace">Ask your memory →</Link><Link className="button secondary" href="/memories">See memories</Link><button className="text-button" onClick={() => {setResult(undefined);setContent("");setTitle("");}}>Add another source</button></div>
      </section>}
    </section>

    <div className="automatic-strip"><span><i>1</i><strong>Ingested</strong><small>Raw source preserved</small></span><b>→</b><span><i>2</i><strong>Remembered</strong><small>Atomic facts extracted</small></span><b>→</b><span><i>3</i><strong>Available</strong><small>Agents get the right context</small></span></div>
  </Page>;
}
