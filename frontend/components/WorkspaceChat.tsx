"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MarkdownAnswer from "@/components/MarkdownAnswer";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";

type Model = { id: string; label: string; company: string; model: string; configured: boolean; default: boolean };
type Project = { id: string; name: string; repository?: string };
type Source = { chunk_id: string; source_title: string; source_type: string; source_url?: string };
type Precedent = { id: string; trigger: string; successes: number; confidence: number };
type Handoff = {
  title: string;
  task: string;
  why: string;
  steps: string[];
  files: string[];
  approval_required: string[];
  prompt: string;
  /* Prior work that already solved this, carried into the agent's prompt. */
  precedents?: Precedent[];
};
type Answer = {
  answer: string;
  answer_sufficient: boolean;
  answer_scope: string;
  evidence: Source[];
  handoff?: Handoff;
  /* Present when the request could land in more than one repository. Offering
     the choice is the whole point — an agent guessing here edits the wrong code. */
  clarification?: {
    question: string;
    detail: string;
    /* "ambiguous_target" offers repositories to pick from; "missing_target" and
       "unresolved_reference" offer examples of the detail the request left out,
       which the asker types. */
    reason?: string;
    options: { project_id?: string; label: string; files?: string[]; hint?: string }[];
  };
  /* What a follow-up like "why is it failing" was bound to. Shown so a wrong
     binding is visible and correctable rather than silently wrong. */
  resolved_subject?: string;
  /* How many connected sources were searched. A count, not a trace — enough to
     say "I looked and found nothing" without exposing how the looking works. */
  searched_sources?: number;
  /* Identifies the context this answer was built from, so what happens next can
     be attributed back to it. Never shown — it is a link, not a statistic. */
  context_event_id?: string;
};
type Run = {
  id: string;
  status: string;
  branch: string;
  base_branch: string;
  commit_sha: string;
  files_changed: string[];
  diff_stat: string;
  pull_request_url: string;
  error: string;
  executor: string;
};
type Turn = { question: string; answer?: Answer; error?: string };

/* Terminal states stop the poller. Anything else is still in flight. */
const RUN_DONE = ["committed", "pushed", "no_changes", "failed"];

/* The thread survives a reload. It is kept per project so switching memory
   spaces does not show someone another project's conversation, and capped so a
   long session cannot outgrow the storage quota. */
const THREAD_KEY = "orgmemory.thread";
const THREAD_LIMIT = 40;

function loadThread(project: string): Turn[] {
  if (typeof window === "undefined" || !project) return [];
  try {
    const stored = window.localStorage.getItem(`${THREAD_KEY}.${project}`);
    const parsed = stored ? JSON.parse(stored) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/* How many prior turns travel with a question. Only the last few carry the live
   subject of a conversation, and the server caps this too — this is about
   sending a sensible payload, not about trusting the client. */
const HISTORY_TURNS = 8;

/* Flatten the thread into the alternating roles the server expects. Clarifying
   questions are left out: they are the assistant asking rather than telling, and
   feeding them back makes the next question look like it was about them. */
function threadHistory(turns: Turn[]): { role: "user" | "assistant"; content: string }[] {
  const history: { role: "user" | "assistant"; content: string }[] = [];
  for (const turn of turns.slice(-HISTORY_TURNS)) {
    if (turn.question) history.push({ role: "user", content: turn.question });
    const answer = turn.answer;
    if (answer?.answer && answer.answer_scope !== "clarification") {
      history.push({ role: "assistant", content: answer.answer.slice(0, 2000) });
    }
  }
  return history;
}

function saveThread(project: string, turns: Turn[]) {
  if (typeof window === "undefined" || !project) return;
  try {
    window.localStorage.setItem(
      `${THREAD_KEY}.${project}`,
      JSON.stringify(turns.slice(-THREAD_LIMIT)),
    );
  } catch {
    /* a full or disabled store must not break the conversation */
  }
}

const starters = [
  "What changed recently?",
  "Who owns this service?",
  "Why is it failing?",
  "What should I know before editing this?",
];

/* The status line names what is happening in plain language. It deliberately
   exposes no counts, ids, or scores — the mechanics belong in the trace, not in
   front of someone waiting for an answer. */
const stages = [
  "Reading your company's memory",
  "Following the trail across sources",
  "Weighing the answers against each other",
  "Writing it up",
];

export default function WorkspaceChat({ user }: { user: any }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState("");
  const [models, setModels] = useState<Model[]>([]);
  const [model, setModel] = useState("");
  const [menu, setMenu] = useState<"" | "model" | "space">("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [loadError, setLoadError] = useState("");
  const [copied, setCopied] = useState("");
  const [restored, setRestored] = useState(false);
  /* Workspace-wide by default: someone asking their company a question is not
     thinking about which repository holds the answer. */
  const [scope, setScope] = useState<"workspace" | "project">("workspace");
  const [filter, setFilter] = useState("");

  const picker = useRef<HTMLDivElement>(null);
  const thread = useRef<HTMLDivElement>(null);
  const stageTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    api<Project[]>("/api/projects")
      .then((items) => {
        setProjects(items);
        if (items[0]) setProject(items[0].id);
      })
      .catch((error) => setLoadError(error.message));
    api<{ models: Model[]; default: string }>("/api/models")
      .then((catalog) => {
        const list = catalog.models || [];
        setModels(list);
        const preferred =
          list.find((item) => item.configured && item.default) ||
          list.find((item) => item.configured) ||
          list.find((item) => item.id === catalog.default) ||
          list[0];
        if (preferred) setModel(preferred.id);
      })
      .catch(() => undefined);
    return () => window.clearInterval(stageTimer.current);
  }, []);

  useEffect(() => {
    if (!menu) return;
    function onPointerDown(event: MouseEvent) {
      if (!picker.current?.contains(event.target as Node)) setMenu("");
    }
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMenu("");
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onEscape);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onEscape);
    };
  }, [menu]);

  useEffect(() => {
    thread.current?.scrollTo({ top: thread.current.scrollHeight, behavior: "smooth" });
  }, [turns, busy]);

  /* Restore on load and whenever the project changes. `restored` gates the save
     below so the empty initial state cannot overwrite a stored thread before
     this has run. */
  useEffect(() => {
    if (!project) return;
    setTurns(loadThread(project));
    setRestored(true);
  }, [project]);

  useEffect(() => {
    if (!restored || !project) return;
    saveThread(project, turns);
  }, [turns, project, restored]);

  const activeModel = useMemo(() => models.find((item) => item.id === model), [models, model]);
  const activeProject = useMemo(() => projects.find((item) => item.id === project), [projects, project]);
  const visibleProjects = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return projects;
    return projects.filter(
      (item) =>
        item.name.toLowerCase().includes(needle) ||
        (item.repository || "").toLowerCase().includes(needle),
    );
  }, [projects, filter]);

  const ask = useCallback(
    async (prompt: string, overrideProject?: string) => {
      const question = prompt.trim();
      const target = overrideProject || project;
      if (!question || !target || busy) return;
      setDraft("");
      setBusy(true);
      setStage(0);
      /* Captured before the new turn is appended, so the thread sent is what came
         before this question rather than including it. */
      const history = threadHistory(turns);
      setTurns((current) => [...current, { question }]);
      stageTimer.current = window.setInterval(
        () => setStage((value) => Math.min(value + 1, stages.length - 1)),
        2200,
      );
      try {
        const response = await api<Answer>("/api/ask", {
          method: "POST",
          body: JSON.stringify({
            project_id: target,
            query: question,
            model: model || undefined,
            surface: "web",
            // Choosing a repository from a clarification answers the question it
            // asked, so that turn is scoped to it rather than searched workspace-wide.
            scope: overrideProject ? "project" : scope,
            history,
          }),
        });
        setTurns((current) =>
          current.map((turn, index) => (index === current.length - 1 ? { ...turn, answer: response } : turn)),
        );
      } catch (error: any) {
        setTurns((current) =>
          current.map((turn, index) => (index === current.length - 1 ? { ...turn, error: error.message } : turn)),
        );
      } finally {
        window.clearInterval(stageTimer.current);
        setBusy(false);
      }
    },
    [busy, model, project, scope, turns],
  );

  async function copyHandoff(handoff: Handoff, key: string, contextEventId?: string) {
    try {
      await navigator.clipboard.writeText(handoff.prompt);
      setCopied(key);
      window.setTimeout(() => setCopied(""), 2200);
      // Copying a handoff is the strongest unprompted signal that an answer was
      // worth acting on, and it costs the person nothing to give.
      noteAction(contextEventId, "handoff_copied", { target: "editor" });
    } catch {
      setCopied("");
    }
  }

  const initials = (user?.display_name || user?.email || "OM")
    .split(/\s+/)
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const workspace = user?.workspaces?.find((item: any) => item.id === user?.active_workspace_id);
  const noProjects = !projects.length && !loadError;

  return (
    <div className="om-home ws-app">
      <header className="ws-bar">
        <Link href="/workspace" className="ws-id" aria-label="OrgMemory">
          <RunbookMark />
          <span>
            <strong>OrgMemory</strong>
            <small>{workspace?.name || "Company brain"}</small>
          </span>
        </Link>

        <div className="ws-controls" ref={picker}>
          {projects.length > 1 && (
            <div className="ws-pick">
              <button className="ws-pill" aria-expanded={menu === "space"} onClick={() => setMenu(menu === "space" ? "" : "space")}>
                <small>Memory</small>
                <span>{scope === "workspace" ? "All memory" : activeProject?.name || "Select"}</span>
                <em aria-hidden="true">▾</em>
              </button>
              {menu === "space" && (
                <div className="ws-menu" role="listbox">
                  <div className="ws-menu-search">
                    <input
                      autoFocus
                      value={filter}
                      placeholder="Filter repositories…"
                      onChange={(event) => setFilter(event.target.value)}
                      aria-label="Filter repositories"
                    />
                  </div>
                  <button
                    role="option"
                    aria-selected={scope === "workspace"}
                    className={scope === "workspace" ? "picked" : ""}
                    onClick={() => {
                      setScope("workspace");
                      setMenu("");
                      setFilter("");
                    }}
                  >
                    <div>
                      <strong>All memory</strong>
                      <small>Search every connected source</small>
                    </div>
                  </button>
                  {visibleProjects.map((item) => (
                    <button
                      key={item.id}
                      role="option"
                      aria-selected={scope === "project" && item.id === project}
                      className={scope === "project" && item.id === project ? "picked" : ""}
                      onClick={() => {
                        setProject(item.id);
                        setScope("project");
                        setMenu("");
                        setFilter("");
                      }}
                    >
                      <div>
                        <strong>{item.name}</strong>
                        {item.repository && <small>{item.repository}</small>}
                      </div>
                    </button>
                  ))}
                  {!visibleProjects.length && <p className="ws-menu-empty">No repository matches that.</p>}
                </div>
              )}
            </div>
          )}

          <div className="ws-pick">
            <button className="ws-pill" aria-expanded={menu === "model"} aria-haspopup="listbox" onClick={() => setMenu(menu === "model" ? "" : "model")}>
              <i className={activeModel?.configured ? "on" : ""} />
              <small>Model</small>
              <span>{activeModel?.label || "—"}</span>
              <em aria-hidden="true">▾</em>
            </button>
            {menu === "model" && (
              <div className="ws-menu" role="listbox">
                {models.map((item) => (
                  <button
                    key={item.id}
                    role="option"
                    aria-selected={item.id === model}
                    className={`${item.configured ? "ready" : ""} ${item.id === model ? "picked" : ""}`}
                    onClick={() => {
                      setModel(item.id);
                      setMenu("");
                    }}
                  >
                    <i />
                    <div>
                      <strong>{item.label}</strong>
                      <small>{item.company}</small>
                    </div>
                    <em>{item.configured ? "Ready" : "Add key"}</em>
                  </button>
                ))}
                <p>
                  Keys live in <Link href="/settings">settings</Link>. Every model answers from the same
                  retrieved company memory.
                </p>
              </div>
            )}
          </div>

          {turns.length > 0 && (
            <button className="ws-pill quiet" onClick={() => setTurns([])} title="Start a new conversation">
              <span>New chat</span>
            </button>
          )}
          <Link className="ws-pill quiet" href="/ingest">
            <span>＋ Knowledge</span>
          </Link>
          <Link className="ws-avatar" href="/account" title="Account and workspace">
            {initials}
          </Link>
        </div>
      </header>

      <main className="ws-thread" ref={thread}>
        <div className="ws-thread-inner">
          {loadError && <div className="ws-alert">{loadError}</div>}

          {noProjects && (
            <section className="ws-onboard">
              <span className="ws-orb" aria-hidden="true">
                <i />
                <RunbookMark />
              </span>
              <h1>Your brain is empty — for about a minute.</h1>
              <p>
                Connect one source and OrgMemory starts answering from it: a repository, a Slack
                workspace, or a document you paste in.
              </p>
              <Link className="home-btn" href="/ingest">
                Connect your first source <span aria-hidden="true">→</span>
              </Link>
            </section>
          )}

          {!noProjects && !turns.length && (
            <section className="ws-rest">
              <span className="ws-orb" aria-hidden="true">
                <i />
                <RunbookMark />
              </span>
              <h1>What do you need to know?</h1>
              <p>Ask about your company, or about anything else. I&rsquo;ll tell you which one I answered from.</p>
              <div className="ws-starters">
                {starters.map((item) => (
                  <button key={item} onClick={() => ask(item)}>
                    {item}
                  </button>
                ))}
              </div>
            </section>
          )}

          {turns.map((turn, index) => (
            <article className="ws-turn" key={`${turn.question}-${index}`}>
              <div className="ws-asked">
                <p>{turn.question}</p>
              </div>

              {turn.error && <div className="ws-alert">{turn.error}</div>}

              {turn.answer && <AnswerBlock answer={turn.answer} onCopy={copyHandoff} copied={copied} turnKey={String(index)} project={project} onPick={(projectId) => ask(turn.question, projectId)} />}

              {!turn.answer && !turn.error && busy && index === turns.length - 1 && (
                <div className="ws-working">
                  <span className="ws-working-dots" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <p>{stages[stage]}…</p>
                </div>
              )}
            </article>
          ))}
        </div>
      </main>

      <footer className="ws-compose-wrap">
        <div className="ws-compose">
          <textarea
            rows={1}
            value={draft}
            disabled={noProjects}
            placeholder={noProjects ? "Connect a source to start asking…" : "Ask anything…"}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                ask(draft);
              }
            }}
            aria-label="Ask OrgMemory"
          />
          <button className="ws-send" onClick={() => ask(draft)} disabled={busy || noProjects || !draft.trim()} aria-label="Send">
            ↑
          </button>
        </div>
        <p className="ws-foot">
          Answers cite the company sources behind them.
          <Link href="/memories">Browse memory</Link>
        </p>
      </footer>
    </div>
  );
}

/* The completion notice. It reports what actually happened to the repository —
   branch, files, commit — because "done" without evidence is not something
   anyone should trust from an agent that edits code on its own. */
function RunCard({ run }: { run: Run }) {
  const working = !RUN_DONE.includes(run.status);

  if (working) {
    return (
      <div className="ws-run working">
        <span className="ws-run-dots" aria-hidden="true"><i /><i /><i /></span>
        <div>
          <strong>{run.executor} is making the change…</strong>
          <small>Working on a branch. Nothing touches your main branch.</small>
        </div>
      </div>
    );
  }

  if (run.status === "failed") {
    return (
      <div className="ws-run failed">
        <strong>Couldn&rsquo;t finish this one.</strong>
        <small>{run.error || "The agent stopped before making a change."}</small>
      </div>
    );
  }

  if (run.status === "no_changes") {
    return (
      <div className="ws-run">
        <strong>Nothing needed changing.</strong>
        <small>The agent read the code and decided it already does this.</small>
      </div>
    );
  }

  return (
    <div className="ws-run done">
      <strong>Done — the change is committed.</strong>
      <dl>
        <div><dt>Branch</dt><dd><code>{run.branch}</code></dd></div>
        {run.commit_sha && <div><dt>Commit</dt><dd><code>{run.commit_sha.slice(0, 10)}</code></dd></div>}
        {run.files_changed.length > 0 && (
          <div><dt>Files</dt><dd>{run.files_changed.map((file) => <code key={file}>{file}</code>)}</dd></div>
        )}
      </dl>
      {run.diff_stat && <pre>{run.diff_stat}</pre>}
      {run.pull_request_url ? (
        <a href={run.pull_request_url} target="_blank" rel="noreferrer">Open the pull request →</a>
      ) : (
        <small>Committed locally on that branch. Review it, then push when you&rsquo;re happy.</small>
      )}
    </div>
  );
}

/* Both writes are deliberately fire-and-forget. Feedback is a side effect of
   using the product; if recording it fails, the person asking should never find
   out — they got their answer either way. */
function noteAction(contextEventId: string | undefined, actionType: string, extra: Record<string, unknown> = {}) {
  if (!contextEventId) return;
  api("/api/outcomes/actions", {
    method: "POST",
    body: JSON.stringify({ context_event_id: contextEventId, action_type: actionType, surface: "web", ...extra }),
  }).catch(() => undefined);
}

function noteOutcome(contextEventId: string | undefined, outcome: "succeeded" | "failed") {
  if (!contextEventId) return;
  api("/api/outcomes/outcomes", {
    method: "POST",
    body: JSON.stringify({ context_event_id: contextEventId, outcome, signal: "human" }),
  }).catch(() => undefined);
}

/* The API answer is written for machines as much as people: it carries a lane
   heading and inline [Source Title] markers. Both are duplicated by the sources
   list below the answer, so they are removed here rather than in the response —
   the payload stays traceable, the reading experience stays clean. */
function readable(answer: string, sources: Source[]) {
  const titles = new Set(sources.map((item) => item.source_title));
  return answer
    .split("\n")
    .filter((line) => !/^\*\*answer from current company memory\*\*$/i.test(line.trim()))
    .map((line) =>
      line.replace(/\s*\[([^[\]]+)\]/g, (marker, label) => (titles.has(label) ? "" : marker)),
    )
    .join("\n")
    .trim();
}

function AnswerBlock({
  answer,
  onCopy,
  copied,
  turnKey,
  project,
  onPick,
}: {
  answer: Answer;
  onCopy: (handoff: Handoff, key: string, contextEventId?: string) => void;
  copied: string;
  turnKey: string;
  project: string;
  onPick: (projectId: string) => void;
}) {
  const [openSources, setOpenSources] = useState(false);
  const [rated, setRated] = useState<"" | "succeeded" | "failed">("");
  const [run, setRun] = useState<Run>();
  const [runError, setRunError] = useState("");
  const sources = answer.evidence || [];

  /* The agent takes minutes, so the run is polled rather than awaited. Polling
     stops on a terminal status, and on unmount so a closed tab stops asking. */
  useEffect(() => {
    if (!run || RUN_DONE.includes(run.status)) return;
    let live = true;
    const timer = window.setInterval(async () => {
      try {
        const next = await api<Run>(`/api/execute/${run.id}`);
        if (!live) return;
        setRun(next);
      } catch {
        /* a transient poll failure should not kill the run display */
      }
    }, 3000);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [run]);

  async function runIt() {
    setRunError("");
    try {
      const started = await api<Run>("/api/execute", {
        method: "POST",
        body: JSON.stringify({
          project_id: project,
          handoff: answer.handoff,
          context_event_id: answer.context_event_id,
        }),
      });
      setRun(started);
    } catch (error: any) {
      setRunError(error.message);
    }
  }

  function rate(outcome: "succeeded" | "failed") {
    setRated(outcome);
    noteAction(answer.context_event_id, outcome === "succeeded" ? "accepted" : "rejected");
    noteOutcome(answer.context_event_id, outcome);
  }

  if (!answer.answer_sufficient) {
    /* Claiming "nothing is connected" to someone with nineteen connected
       repositories is simply false, and it sends them to a page that will not
       help. What is true is narrower: this search came back empty. */
    const searched = answer.searched_sources ?? 0;
    return (
      <div className="ws-answer">
        <div className="ws-withheld">
          <strong>I couldn&rsquo;t find this in your company&rsquo;s memory.</strong>
          {searched > 0 ? (
            <>
              <p>
                I searched {searched === 1 ? "1 connected source" : `${searched} connected sources`}{" "}
                and found nothing that answers this. Guessing about your company is worse than
                saying so &mdash; but the question may just need a name I can match on.
              </p>
              <p className="ws-withheld-try">
                Try naming the service, repository, or file &mdash; or the error you&rsquo;re
                looking at. If it lives somewhere I&rsquo;m not connected to yet, add it.
              </p>
            </>
          ) : (
            <p>
              Nothing is connected yet, so there is no memory to search. Connect the source that
              would know, and ask again.
            </p>
          )}
          <Link className="home-link" href="/ingest">
            {searched > 0 ? "Connect another source" : "Connect a source"}{" "}
            <span aria-hidden="true">→</span>
          </Link>
        </div>
      </div>
    );
  }

  if (answer.clarification) {
    return (
      <div className="ws-answer">
        <div className="ws-clarify">
          <strong>{answer.clarification.question}</strong>
          <p>{answer.clarification.detail}</p>
          <div className="ws-clarify-options">
            {answer.clarification.options.map((option, index) =>
              option.project_id ? (
                <button key={option.project_id} onClick={() => onPick(option.project_id!)}>
                  <span>{option.label}</span>
                  {(option.files?.length ?? 0) > 0 && (
                    <small>{option.files!.slice(0, 2).join(", ")}</small>
                  )}
                </button>
              ) : (
                /* Nothing to click: only the asker knows the answer, so these are
                   examples of the shape it should take, not choices to make. */
                <div className="ws-clarify-example" key={`${option.label}-${index}`}>
                  <span>{option.label}</span>
                  {option.hint && <small>{option.hint}</small>}
                </div>
              ),
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="ws-answer">
      <MarkdownAnswer>{readable(answer.answer, sources)}</MarkdownAnswer>

      {answer.resolved_subject && (
        /* A follow-up was bound to an earlier subject. Saying which one turns a
           silent wrong guess into an obvious one the person can correct. */
        <p className="ws-scope">Answered about: {answer.resolved_subject}</p>
      )}

      {answer.answer_scope === "general_knowledge" && (
        <p className="ws-scope">General knowledge — not from your company&rsquo;s memory.</p>
      )}

      {answer.handoff && (
        <section className="ws-handoff">
          <header>
            <span>Ready for your editor</span>
            <div className="ws-handoff-actions">
              <button className="quiet" onClick={() => onCopy(answer.handoff!, turnKey, answer.context_event_id)}>
                {copied === turnKey ? "Copied" : "Copy"}
              </button>
              <button onClick={runIt} disabled={Boolean(run)}>
                {run ? "Running…" : "Do it for me"}
              </button>
            </div>
          </header>
          <strong>{answer.handoff.task}</strong>
          {answer.handoff.files.length > 0 && (
            <div className="ws-handoff-files">
              {answer.handoff.files.map((file) => (
                <code key={file}>{file}</code>
              ))}
            </div>
          )}
          {(answer.handoff.precedents?.length ?? 0) > 0 && (
            <div className="ws-precedent">
              <span>This has been done before</span>
              <ul>
                {answer.handoff.precedents!.map((item) => (
                  <li key={item.id}>
                    {item.trigger}
                    <small>worked {item.successes}×</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p>Paste into Cursor, Copilot, or Claude Code. It carries only the context this task needs.</p>
          {answer.handoff.approval_required.length > 0 && (
            <small>Needs your approval before anything is applied.</small>
          )}
          {runError && <p className="ws-run-error">{runError}</p>}
          {run && <RunCard run={run} />}
        </section>
      )}

      {answer.context_event_id && (
        <div className="ws-rate">
          {rated ? (
            <span className="ws-rate-done">
              {rated === "succeeded" ? "Noted — thanks." : "Noted. I'll weigh this differently next time."}
            </span>
          ) : (
            <>
              <span>Did this work?</span>
              <button onClick={() => rate("succeeded")}>Yes</button>
              <button onClick={() => rate("failed")}>No</button>
            </>
          )}
        </div>
      )}

      {sources.length > 0 && (
        <div className={`ws-sources ${openSources ? "open" : ""}`}>
          <button onClick={() => setOpenSources((open) => !open)}>
            {sources.length} source{sources.length === 1 ? "" : "s"}
            <em aria-hidden="true">{openSources ? "▴" : "▾"}</em>
          </button>
          {openSources && (
            <ul>
              {sources.map((item) => (
                <li key={item.chunk_id}>
                  {item.source_url ? (
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      {item.source_title}
                    </a>
                  ) : (
                    <span>{item.source_title}</span>
                  )}
                  <small>{item.source_type.replace(/_/g, " ")}</small>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
