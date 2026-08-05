"use client";

import { useEffect, useState } from "react";
import Page from "@/components/Page";
import MarkdownAnswer from "@/components/MarkdownAnswer";
import { api, formatDate } from "@/lib/api";

const starters = [
  "What does this service do?",
  "What changed recently?",
  "What was the last commit?",
  "What should I know before editing this repo?",
];

const TEMPORAL_QUESTION = /\b(last|latest|newest|recent|recently|changed|changes|commit)\b/i;

function score(value: number) {
  return `${Math.round((value || 0) * 100)}%`;
}

function EvidenceTree({ query, result }: { query: string; result: any }) {
  const evidence = result.evidence || [];
  const service = result.related_services?.[0];
  const trace = result.retrieval_trace;
  return <section className="memory-tree panel">
    <div className="panel-head">
      <div><span className="panel-label">Memory path</span><h2>Why OrgMemory selected this context</h2></div>
      <span>{evidence.length} sources</span>
    </div>
    <div className="memory-tree-body">
      <div className="tree-node tree-question"><span>Question</span><strong>{query}</strong></div>
      <div className="tree-line" />
      <div className="tree-node tree-context"><span>Resolved context</span><strong>{service || trace?.context_window || "Project knowledge"}</strong><small>{trace?.context_reused ? "Carried from the previous turn" : "Established for this question"}</small></div>
      <div className="tree-branches">
        {evidence.length ? evidence.slice(0, 6).map((item: any, index: number) => <article key={item.chunk_id}>
          <i />
          <div><span>{String(index + 1).padStart(2, "0")} · {item.source_type.replace(/_/g, " ")}</span><strong>{item.source_title}</strong><small>{score(item.confidence)} retrieval match</small></div>
        </article>) : <div className="tree-empty">No evidence branch met the answer threshold.</div>}
      </div>
    </div>
  </section>;
}

export default function Ask() {
  const [projects, setProjects] = useState<any[]>([]);
  const [project, setProject] = useState("");
  const [models, setModels] = useState<any[]>([]);
  const [model, setModel] = useState("gpt");
  const [query, setQuery] = useState("");
  const [lastQuery, setLastQuery] = useState("");
  const [context, setContext] = useState<any>();
  const [result, setResult] = useState<any>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [syncBusy, setSyncBusy] = useState(false);
  const [busyStage, setBusyStage] = useState("Building a current evidence pack");

  useEffect(() => {
    api<any[]>("/api/projects").then(items => {
      setProjects(items);
      if (items[0]) setProject(items[0].id);
    }).catch(requestError => setError(requestError.message));
    api<any>("/api/models").then(catalog => {
      setModels(catalog.models || []);
      const preferred = catalog.models?.find((item:any) => item.default && item.configured)
        || catalog.models?.find((item:any) => item.configured)
        || catalog.models?.find((item:any) => item.id === catalog.default)
        || catalog.models?.[0];
      if (preferred) setModel(preferred.id);
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    setResult(undefined);
    setHistory([]);
    if (!project) return;
    api(`/api/projects/${project}/context`).then(setContext).catch(requestError => setError(requestError.message));
  }, [project]);

  async function refreshRepository(announce = true) {
    const selected = projects.find(item => item.id === project);
    if (!selected?.repository) {
      if (announce) setMessage("This project uses uploaded memory and has no GitHub repository to refresh.");
      return;
    }
    setSyncBusy(true);
    if (announce) { setError(""); setMessage(""); }
    try {
      const response: any = await api("/api/ingest/github", {
        method: "POST",
        body: JSON.stringify({repo_url_or_path: selected.repository, project_name: selected.name}),
      });
      const changed = response.change?.changed_files?.length || 0;
      if (announce) {
        setMessage(changed
          ? `Memory refreshed from GitHub · ${changed} changed file${changed === 1 ? "" : "s"} indexed.`
          : "Memory refreshed from GitHub · already current.");
        setResult(undefined);
        setHistory([]);
      }
      setContext(await api(`/api/projects/${project}/context`));
      return response;
    } finally {
      setSyncBusy(false);
    }
  }

  async function manualRefresh() {
    try { await refreshRepository(true); }
    catch (requestError: any) { setError(requestError.message); }
  }

  async function ask() {
    const question = query.trim();
    if (!project || !question) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const selected = projects.find(item => item.id === project);
      if (TEMPORAL_QUESTION.test(question) && selected?.repository) {
        setBusyStage("Checking GitHub for newer changes");
        try {
          await refreshRepository(false);
        } catch (refreshError: any) {
          setMessage(`Live GitHub refresh was unavailable. Answering from indexed memory: ${refreshError.message}`);
        }
      }
      setBusyStage("Activating the context swarm");
      const response = await api("/api/ask", {
        method: "POST",
        body: JSON.stringify({
          project_id: project,
          query: `@orgmemory ${question.replace(/^@(runbook|orgmemory)\s*/i, "")}`,
          model,
        }),
      });
      setLastQuery(question);
      setResult(response);
      setHistory(current => [...current, {query: question, result: response}].slice(-8));
      setQuery("");
      setContext(await api(`/api/projects/${project}/context`));
    } catch (requestError: any) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      setBusyStage("Building a current evidence pack");
    }
  }

  async function saveBrief() {
    setError("");
    setMessage("");
    try {
      const response: any = await api("/api/memory/artifacts", {
        method: "POST",
        body: JSON.stringify({
          project_id: project,
          name: lastQuery.slice(0, 120),
          artifact_type: "brief",
          content: `# ${lastQuery}\n\n${result.answer}`,
          source_ids: Array.from(new Set(result.evidence.map((item:any) => item.source_id).filter(Boolean))),
          memory_ids: result.memory_units.map((item:any) => item.id),
          context_envelope_id: result.context_envelope?.id || "",
        }),
      });
      setMessage(`Saved ${response.name} as a revision-tracked memory artifact.`);
    } catch (requestError: any) {
      setError(requestError.message);
    }
  }

  const trace = result?.retrieval_trace;
  const trust = result?.trust_score;
  const activationSwarm = trace?.plan?.context_activation_swarm;
  const activationRun = activationSwarm?.runs?.find(
    (item: any) => item.run_id === activationSwarm?.active_run_id,
  ) || activationSwarm?.runs?.at(-1);
  const noEvidence = result && !result.evidence?.length;
  const selectedProject = projects.find(item => item.id === project);
  const temporalAnswer = ["commit_history", "recent_changes", "semantic_change"].includes(result?.answer_kind);

  return <Page
    eyebrow="Company memory"
    title="Ask OrgMemory"
    description="Ask across the company brain. The retrieval swarm builds one source-backed context, then your selected model explains it."
    action={<div className="ask-head-controls"><label><span>Memory space</span><select className="project-select" value={project} onChange={event => setProject(event.target.value)}>{projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label><span>Answer model</span><select value={model} onChange={event => setModel(event.target.value)}>{models.map(item => <option key={item.id} value={item.id}>{item.label}{item.configured ? "" : " · add API key"}</option>)}</select></label></div>}
  >
    {error && <div className="notice error">{error}</div>}
    {message && <div className="notice">{message}</div>}

    <section className="ask-surface">
      <header className="ask-memory-bar">
        <div><span className="memory-dot" /><strong>{context?.project?.name || "Select a project"}</strong></div>
        <span>{context?.continuity?.active_service || "No service pinned"}</span>
        <span>{context?.continuity?.query_count || 0} prior questions</span>
        <span>Evidence updated {formatDate(context?.knowledge?.last_ingested_at)}</span>
        {selectedProject?.repository && <button className="memory-refresh" disabled={syncBusy || busy} onClick={manualRefresh}><i />{syncBusy ? "Syncing…" : "Refresh GitHub"}</button>}
      </header>

      <div className="ask-transcript">
        {!history.length && !busy && <div className="ask-empty-state">
          <span className="ask-empty-mark">O</span>
          <h2>What do you need to know?</h2>
          <p>OrgMemory selects current memories for this project, then traces every claim to its source.</p>
        </div>}

        {history.slice(0, -1).map((turn, index) => <div className="thread-turn compact" key={`${turn.query}-${index}`}>
          <div className="thread-question"><span>You</span><p>{turn.query}</p></div>
          <div className="thread-answer"><span>OrgMemory</span><MarkdownAnswer>{turn.result.answer}</MarkdownAnswer><small>{turn.result.evidence?.length || 0} citations · {score(turn.result.confidence)}</small></div>
        </div>)}

        {busy && <div className="ask-thinking"><span className="thinking-orbit"><i/><i/><i/></span><div><strong>{busyStage}</strong><small>{busyStage.startsWith("Checking") ? "Reading the newest commits before answering" : "Routing context, checking recency, and verifying citations"}</small></div></div>}

        {result && !busy && <div className={`thread-turn current ${noEvidence ? "withheld" : ""}`}>
          <div className="thread-question"><span>You</span><p>{lastQuery}</p></div>
          <div className="thread-answer"><div className="thread-answer-head"><span>OrgMemory</span><div className="answer-head-badges"><small>{result.model?.used ? `${result.model.label} · ${result.model.model}` : "Deterministic grounding"}</small><span className={`badge ${noEvidence ? "danger" : trust?.level === "high" ? "success" : "warning"}`}>{noEvidence ? "not enough memory" : `${score(trust?.score || result.confidence)} grounded`}</span></div></div>{temporalAnswer && <div className="answer-freshness"><i/> {result.answer_kind === "semantic_change" ? "Belief history checked before this answer" : "GitHub history checked before this answer"}</div>}<MarkdownAnswer>{result.answer}</MarkdownAnswer>{result.diagnostic && result.likely_cause && !noEvidence && result.likely_cause !== "Insufficient evidence" && <div className="answer-cause"><small>Most likely cause</small><strong>{result.likely_cause}</strong></div>}<div className="answer-meta"><span>{score(result.confidence)} answer confidence</span><span>{result.evidence.length} source{result.evidence.length === 1 ? "" : "s"}</span><span>{result.memory_units?.length || 0} matching memories</span>{trace?.context_reused && <span>Context carried forward</span>}</div>{!noEvidence && <details className="why-answer-inline"><summary>View sources and retrieval reasoning</summary><div>{result.evidence.slice(0, 4).map((item:any, index:number)=><article key={item.chunk_id}><div><strong>{index + 1}. {item.source_title}</strong><span>{score(item.confidence)} relevance</span></div>{item.section && <small>{item.section}</small>}<pre>{item.exact_chunk}</pre>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open exact source ↗</a>}</article>)}</div></details>}</div>
        </div>}
      </div>

      <div className="ask-compose">
        <textarea aria-label="Ask OrgMemory" value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") ask(); }} placeholder="Ask across code, conversations, decisions, owners, incidents, and company history…" />
        <button className="button" disabled={busy || !project || !query.trim()} onClick={ask}>{busy ? "Working…" : "Ask →"}</button>
      </div>
      <div className="ask-starters">{starters.map(item => <button key={item} onClick={() => setQuery(item)}>{item}</button>)}</div>
    </section>

    {result && <div className="ask-evidence-layout">
      <div className="stack">
        <EvidenceTree query={lastQuery} result={result} />
        <section className="panel evidence-ledger">
          <div className="panel-head"><div><span className="panel-label">Sources</span><h2>Evidence used in this answer</h2></div><span>{result.evidence.length} cited</span></div>
          <div className="panel-body">{result.evidence.length ? result.evidence.map((item: any, index: number) => <article className="clean-source-row" key={item.chunk_id}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div><div className="row between"><strong>{item.source_title}</strong><small>{item.source_type.replace(/_/g, " ")}</small></div>{item.project_name && <span className="source-project">{item.project_name}</span>}<p>{item.snippet}</p>{item.source_url && <a href={item.source_url} target="_blank" rel="noreferrer">Open source ↗</a>}</div>
          </article>) : <div className="empty">OrgMemory does not have enough company memory to answer this confidently.</div>}</div>
        </section>
      </div>

      <aside className="ask-evidence-rail stack">
        <section className="rail-panel answer-confidence-card"><span className="panel-label">Answer quality</span><strong>{score(trust?.score || 0)}</strong><p>{trust?.reason || "No trust asserted without supporting evidence."}</p><dl><div><dt>Retrieval</dt><dd>{score(result.confidence)}</dd></div><div><dt>Sources</dt><dd>{result.evidence.length}</dd></div><div><dt>Graph paths</dt><dd>{trace?.graph_paths?.length || 0}</dd></div></dl></section>

        {!noEvidence && <button className="button secondary full-button" onClick={saveBrief}>Save memory-backed brief</button>}

        <details className="rail-panel clean-details"><summary>Dynamic context envelope</summary><dl><div><dt>Context ID</dt><dd>{result.context_envelope?.id || "—"}</dd></div><div><dt>Window</dt><dd>{trace?.context_window}</dd></div><div><dt>Intent</dt><dd>{trace?.query_type?.replace(/_/g, " ")}</dd></div><div><dt>Scope</dt><dd>{trace?.scope_mode === "workspace" ? "Explicit workspace search" : "Active repository"}</dd></div><div><dt>Authorized teams</dt><dd>{result.context_envelope?.authorized_team_ids?.length || "Workspace admin"}</dd></div><div><dt>Source versions</dt><dd>{Object.keys(result.context_envelope?.source_version_vector || {}).length}</dd></div><div><dt>Activation swarm</dt><dd>{activationRun ? `${activationRun.agents?.filter((item:any) => item.status === "complete").length || 0}/${activationRun.agents?.length || 0} agents` : "—"}</dd></div><div><dt>Swarm status</dt><dd>{activationRun?.status || "—"}</dd></div><div><dt>Compiled context</dt><dd>{activationSwarm?.compiled_context?.token_count || 0} / {activationSwarm?.compiled_context?.evidence_token_budget || 0} tokens</dd></div><div><dt>Token budget</dt><dd>{result.context_envelope?.token_budget || 6000}</dd></div><div><dt>Selection policy</dt><dd>{trace?.context_selection_policy}</dd></div><div><dt>Scope reason</dt><dd>{trace?.scope_reason}</dd></div><div><dt>Strategy</dt><dd>{trace?.plan?.activation_strategy || trace?.plan?.retrieval_strategy || trace?.engine}</dd></div></dl></details>

        {Boolean(result.safe_actions?.length || result.approval_required?.length) && <details className="rail-panel clean-details"><summary>Action boundary</summary>{result.safe_actions?.map((action: string) => <p key={action} className="safe-line">✓ {action}</p>)}{result.approval_required?.map((action: string) => <p key={action} className="approval-line">! {action}</p>)}</details>}

        {result.change_correlation?.suspects?.length ? <details className="rail-panel clean-details"><summary>Correlated changes</summary>{result.change_correlation.suspects.slice(0, 4).map((suspect: any) => <p key={suspect.item_id}><strong>{suspect.title}</strong><br />{suspect.reason}</p>)}</details> : null}
      </aside>
    </div>}
  </Page>;
}
