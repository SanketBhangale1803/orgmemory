"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";
import type {
  OrgMemoryBriefing,
  OrgMemoryBriefingCitation,
  WebMCPActivity,
} from "@/lib/webmcp";
import {
  WEBMCP_GOVERNED_TOOL_COUNT,
  WEBMCP_READ_TOOL_COUNT,
  WEBMCP_TOOL_CATALOG,
} from "@/lib/webmcpCatalog";

/* The console runs a REAL agent (the workspace's configured model) over the
   page's WebMCP tool surface. Session 1 investigates and proposes; a human
   approves; Session 2 is a brand-new agent with zero conversation memory that
   answers only because the previous agent's verified knowledge is now in
   OrgMemory. That handoff is the product. */

const DEMO_PROJECT_NAME = "WebMCP Demo";
const DEMO_SERVICE = "payments";

/* Two intents with genuinely different verdicts. A demo where every example
   returns "requires approval" teaches nothing about the boundary. */
const BRIEFING_EXAMPLES = [
  { task: "restart the payments connection pool", service: "payments" },
  { task: "raise worker concurrency on payments", service: "payments" },
  { task: "read the checkout latency dashboard", service: "checkout" },
] as const;

const SESSION_ONE_QUESTION = "Why is the payments service failing again?";
const SESSION_TWO_QUESTION =
  "Payments is alerting again. What should we check first, and what has worked before?";

const DEMO_SEEDS = [
  {
    kind: "incident",
    subject: "payments outage: PostgreSQL connection-pool exhaustion",
    content:
      "Payments failed for 40 minutes. The connection pool on the shared PostgreSQL cluster was exhausted after worker concurrency was raised the day before. Resolved by rolling concurrency back and restarting the pool.",
    service: DEMO_SERVICE,
    reason: "Post-mortem reviewed and published by the platform team.",
  },
  {
    kind: "incident",
    subject: "payments degraded: checkout timeouts",
    content:
      "Checkout latency spiked and requests timed out. Payments worker pool exhaustion during the nightly batch job starved the checkout path. Mitigated by moving the batch off business hours.",
    service: DEMO_SERVICE,
    reason: "Confirmed in the incident channel with linked monitoring.",
  },
  {
    kind: "decision",
    subject: "cap payments worker concurrency",
    content:
      "The team decided to cap payments worker concurrency to protect the shared PostgreSQL connection pool instead of introducing per-service pools.",
    service: DEMO_SERVICE,
    reason: "Recorded decision from the platform architecture review.",
  },
  {
    kind: "dependency",
    subject: "payments depends on the shared PostgreSQL cluster",
    content:
      "Payments shares the PostgreSQL cluster with the ledger service; pool exhaustion on either affects the other.",
    service: DEMO_SERVICE,
    reason: "Confirmed against the deployment manifest and the service owner.",
  },
  {
    kind: "procedure",
    subject: "payments pool exhaustion first response",
    content:
      "1) Check the PostgreSQL connection-count dashboard. 2) Compare active worker concurrency against the configured cap. 3) Restart the payments pool if saturation holds. 4) Page the Payments Platform on-call if the cap itself was raised.",
    service: DEMO_SERVICE,
    reason: "Validated during the last two incidents.",
  },
] as const;

type Project = { id: string; name: string; repository?: string };
type Proposal = {
  id: string;
  project_id: string;
  kind: string;
  subject: string;
  content: string;
  reason?: string;
  status: "pending_approval" | "approved" | "denied";
  memory_id?: string;
};
type AgentStep = {
  tool: string;
  arguments: Record<string, unknown>;
  summary: string;
  thought?: string;
  observation?: string;
  duration_ms?: number;
};
type AgentSession = {
  id: string;
  question: string;
  model: string;
  status: "running" | "complete" | "error";
  steps: AgentStep[];
  answer: string;
  memory_ids: string[];
  proposal: Proposal | null;
  error: string;
  mode?: "model" | "guided";
};

export default function WebMCPDemo() {
  const [user, setUser] = useState<any>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [spaceId, setSpaceId] = useState("");
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [sessions, setSessions] = useState<Record<string, AgentSession>>({});
  const [running, setRunning] = useState<"" | "one" | "two">("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState<boolean | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [recentActivity, setRecentActivity] = useState<WebMCPActivity[]>([]);
  const [toolFilter, setToolFilter] = useState<"all" | "read-only" | "governed">("all");
  const [briefTask, setBriefTask] = useState<string>(BRIEFING_EXAMPLES[0].task);
  const [briefService, setBriefService] = useState<string>(BRIEFING_EXAMPLES[0].service);
  const [brief, setBrief] = useState<OrgMemoryBriefing | null>(null);
  const [briefing, setBriefing] = useState(false);
  const [briefError, setBriefError] = useState("");
  const pollRef = useRef<number | undefined>(undefined);

  const isAdmin = user?.role === "owner" || user?.role === "admin";
  const demoProject = projects.find((project) => project.name === DEMO_PROJECT_NAME) || null;
  const activeSpace = spaceId || demoProject?.id || projects[0]?.id || "";

  const approvedSeeds = proposals.filter(
    (proposal) => proposal.status === "approved" && proposal.project_id === activeSpace,
  );
  const pendingProposals = proposals.filter(
    (proposal) => proposal.status === "pending_approval" && proposal.project_id === activeSpace,
  );
  const memoryReady = approvedSeeds.length >= 3;
  const sessionOne = sessions.one;
  const sessionTwo = sessions.two;

  useEffect(() => {
    setSupported(typeof document !== "undefined" && Boolean(document.modelContext));
    api<any>("/api/auth/me")
      .then(setUser)
      .catch(() => setUser({}));
    api<Project[]>("/api/projects")
      .then((items) => {
        setProjects(items);
        const demo = items.find((project) => project.name === DEMO_PROJECT_NAME);
        setSpaceId(demo?.id || items[0]?.id || "");
      })
      .catch(() => undefined);
    api<Proposal[]>("/api/memory/proposals")
      .then(setProposals)
      .catch(() => undefined);
    try {
      const stored = JSON.parse(window.sessionStorage.getItem("orgmemory.webmcp-activity") || "[]");
      if (Array.isArray(stored)) setRecentActivity(stored.slice(-12));
    } catch {
      /* Recent activity is optional context, never an execution dependency. */
    }
    function onActivity(event: Event) {
      const activity = (event as CustomEvent<WebMCPActivity>).detail;
      if (!activity) return;
      setRecentActivity((current) => {
        const index = current.findIndex((item) => item.id === activity.id);
        return (index === -1
          ? [...current, activity]
          : current.map((item, itemIndex) => (itemIndex === index ? activity : item))).slice(-12);
      });
    }
    window.addEventListener("orgmemory:webmcp-activity", onActivity);
    return () => window.removeEventListener("orgmemory:webmcp-activity", onActivity);
  }, []);

  const watch = useCallback((lane: "one" | "two", runId: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    const poll = async () => {
      try {
        const next = await api<AgentSession>(`/api/webmcp/agent-sessions/${runId}`);
        setSessions((current) => ({ ...current, [lane]: next }));
        if (next.status !== "running") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          setRunning("");
          if (next.proposal?.id) {
            api<Proposal[]>("/api/memory/proposals")
              .then(setProposals)
              .catch(() => undefined);
          }
        }
      } catch {
        if (pollRef.current) window.clearInterval(pollRef.current);
        setRunning("");
      }
    };
    pollRef.current = window.setInterval(poll, 900);
  }, []);

  useEffect(() => () => window.clearInterval(pollRef.current), []);

  async function runSession(lane: "one" | "two") {
    if (!activeSpace) return;
    setError("");
    setNote("");
    setRunning(lane);
    const question = lane === "one" ? SESSION_ONE_QUESTION : SESSION_TWO_QUESTION;
    // A fresh session every run: Session 2 shares NOTHING with Session 1
    // except the workspace itself. That is the entire claim being demonstrated.
    setSessions((current) => ({ ...current, [lane]: undefined as unknown as AgentSession }));
    try {
      const started = await api<AgentSession>("/api/webmcp/agent-sessions", {
        method: "POST",
        body: JSON.stringify({ question, project_id: activeSpace }),
      });
      setSessions((current) => ({ ...current, [lane]: started }));
      watch(lane, started.id);
    } catch (e: any) {
      setError(e.message);
      setRunning("");
    }
  }

  async function runBriefing() {
    setBriefError("");
    setBriefing(true);
    try {
      setBrief(
        await api<OrgMemoryBriefing>("/api/briefings", {
          method: "POST",
          body: JSON.stringify({
            task: briefTask.trim(),
            service: briefService.trim(),
            project_id: activeSpace || "",
            surface: "webmcp-demo",
          }),
        }),
      );
    } catch (e: any) {
      setBriefError(e.message);
    } finally {
      setBriefing(false);
    }
  }

  async function prepareDemoSpace() {
    setError("");
    setPreparing(true);
    try {
      let project = demoProject;
      if (!project) {
        project = await api<Project>("/api/projects", {
          method: "POST",
          body: JSON.stringify({ name: DEMO_PROJECT_NAME }),
        });
        setProjects((current) => [...current, project as Project]);
        setSpaceId(project.id);
      }
      const seeded: Proposal[] = [];
      for (const seed of DEMO_SEEDS) {
        seeded.push(
          await api<Proposal>("/api/memory/proposals", {
            method: "POST",
            body: JSON.stringify({ project_id: project.id, ...seed }),
          }),
        );
      }
      setProposals((current) => {
        const known = new Set(current.map((proposal) => proposal.id));
        return [...current, ...seeded.filter((proposal) => !known.has(proposal.id))];
      });
      setNote(
        "The demo dataset is queued as proposals. Approve them below — that human decision is the boundary agents work inside.",
      );
    } catch (e: any) {
      setError(e.message);
    } finally {
      setPreparing(false);
    }
  }

  async function approve(proposal: Proposal) {
    setError("");
    try {
      const resolved = await api<Proposal>(
        `/api/memory/proposals/${encodeURIComponent(proposal.id)}/resolve`,
        { method: "POST", body: JSON.stringify({ approved: true }) },
      );
      setProposals((current) =>
        current.map((item) => (item.id === resolved.id ? resolved : item)),
      );
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function approveAll() {
    for (const proposal of pendingProposals) {
      await approve(proposal);
    }
    setNote("Approved. This knowledge is now searchable by any agent, in any session, forever.");
  }

  const waitingOnHuman = pendingProposals.length > 0;
  const canRunTwo = Boolean(
    sessionOne &&
      sessionOne.status === "complete" &&
      !running &&
      (memoryReady || (sessionOne.proposal && approvedSeeds.length >= 3)),
  );

  return (
    <div className="webmcp-page webmcp-command-center">
      <header className="webmcp-hero">
        <Link href="/" className="webmcp-brand" aria-label="OrgMemory home">
          <RunbookMark />
          <span>
            <strong>OrgMemory</strong>
            <small>WebMCP</small>
          </span>
        </Link>
        <nav className="webmcp-nav">
          <Link href="/workspace">Open workspace</Link>
        </nav>
      </header>

      <main className="webmcp-main">
        <section className="webmcp-intro">
          <p className="webmcp-eyebrow">WebMCP Command Center</p>
          <h1>Brief the agent before it changes production.</h1>
          <p className="webmcp-lede">
            Without WebMCP, an agent sees another website. In the authenticated workspace,
            OrgMemory registers a browser-native Model Context Provider, so an agent working
            anywhere on the web can ask what this engineering organization already knows —
            the decisions that constrain a change, the incidents that started the same way,
            the blast radius — and then report back what actually happened.
          </p>
          <div className="webmcp-flow" aria-label="How it works">
            <span>browser agent</span>
            <i aria-hidden="true">→</i>
            <span>get_orgmemory_briefing</span>
            <i aria-hidden="true">→</i>
            <span>constraints, history, blast radius</span>
            <i aria-hidden="true">→</i>
            <span>human approves the change</span>
            <i aria-hidden="true">→</i>
            <span>record_orgmemory_outcome</span>
          </div>
          <p className="webmcp-boundary">
            <strong>Capability is not authorization.</strong> Three tiers, and an agent can tell
            them apart from the annotations alone: reads are permission-trimmed on the server;
            an outcome report appends to the ledger and changes no knowledge; and the only way a
            single fact enters company memory is a proposal a person approves. Everything an
            agent reads is data, never instructions.
          </p>
        </section>

        <section className="wmcp-command-overview">
          <div className="wmcp-command-status">
            <span className={`wmcp-command-orb ${recentActivity.length ? "connected" : ""}`} aria-hidden="true"><i />✦</span>
            <div>
              <p>Agent interface</p>
              <strong>{recentActivity.length ? "Agent activity observed" : supported ? "WebMCP-capable browser detected" : "WebMCP workspace ready"}</strong>
              <span>{recentActivity.length ? `${recentActivity.length} recent tool calls from the workspace.` : "Open the workspace to register the authenticated tool surface."}</span>
            </div>
            <Link href="/workspace">Open live workspace <span aria-hidden="true">→</span></Link>
          </div>
          <div className="wmcp-command-metrics">
            <div><strong>{WEBMCP_TOOL_CATALOG.length}</strong><span>tools exposed</span></div>
            <div><strong>{WEBMCP_READ_TOOL_COUNT}</strong><span>read-only</span></div>
            <div><strong>{WEBMCP_GOVERNED_TOOL_COUNT}</strong><span>human-governed</span></div>
          </div>
        </section>

        <section className="wmcp-command-trace">
          <header>
            <div><p className="webmcp-eyebrow">Observable, not opaque</p><h2>WebMCP live trace</h2></div>
            <span>Browser agent → WebMCP → OrgMemory → evidence</span>
          </header>
          {recentActivity.length ? (
            <ol>
              {recentActivity.map((activity, index) => (
                <li key={activity.id} className={activity.state}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <header><code>{activity.tool}</code><em>{activity.durationMs != null ? `${activity.durationMs} ms` : activity.state}</em></header>
                    <p>{activity.inputSummary}</p>
                    {activity.resultSummary && <strong>{activity.resultCount != null ? `${activity.resultCount} results · ` : ""}{activity.resultSummary}</strong>}
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <div className="wmcp-command-empty">
              <span aria-hidden="true">✦</span>
              <strong>Waiting for a real browser-agent call</strong>
              <p>Open the workspace in a WebMCP-capable browser and invoke a tool. The trace is populated only by actual calls—there is no decorative playback.</p>
              <Link href="/workspace">Go to the live tool surface</Link>
            </div>
          )}
        </section>

        <section className="wmcp-comparison">
          <header><p className="webmcp-eyebrow">Why WebMCP</p><h2>From interface archaeology to a direct capability.</h2></header>
          <div>
            <article>
              <span>Without WebMCP</span>
              <ol><li>Inspect DOM</li><li>Guess the right control</li><li>Navigate and parse UI</li><li>Hope context survived</li></ol>
            </article>
            <i aria-hidden="true">→</i>
            <article className="with">
              <span>With WebMCP</span>
              <code>get_orgmemory_briefing(&#123; task, service &#125;)</code>
              <strong>Constraints, prior incidents, blast radius — before the change</strong>
            </article>
          </div>
        </section>

        <section className="wmcp-briefing" aria-label="Live pre-action briefing">
          <header>
            <div>
              <p className="webmcp-eyebrow">The tool the product exists for</p>
              <h2>Ask before you act, from anywhere on the web.</h2>
            </div>
            <span>get_orgmemory_briefing</span>
          </header>
          <p className="webmcp-note">
            Describe a change the way an agent would, and this calls the real endpoint against
            your workspace. No model runs: every line below is a stored memory with an id you
            can open, which is why the same intent returns the same verdict twice.
          </p>

          {!user?.id ? (
            <p className="webmcp-note">
              <Link href="/login">Sign in</Link> to run a briefing against your own memory.
            </p>
          ) : (
            <>
              <form
                className="wmcp-brief-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void runBriefing();
                }}
              >
                <input
                  aria-label="What the agent is about to do"
                  value={briefTask}
                  onChange={(event) => setBriefTask(event.target.value)}
                  placeholder="What is the agent about to do?"
                />
                <input
                  aria-label="Service"
                  className="wmcp-brief-service"
                  value={briefService}
                  onChange={(event) => setBriefService(event.target.value)}
                  placeholder="service"
                />
                <button className="home-btn" type="submit" disabled={briefing || !briefTask.trim()}>
                  {briefing ? "Briefing…" : "Brief me"}
                </button>
              </form>
              <div className="wmcp-brief-examples">
                <span>Try</span>
                {BRIEFING_EXAMPLES.map((example) => (
                  <button
                    key={example.task}
                    type="button"
                    onClick={() => {
                      setBriefTask(example.task);
                      setBriefService(example.service);
                    }}
                  >
                    {example.task}
                  </button>
                ))}
              </div>

              {briefError && <p className="webmcp-error">{briefError}</p>}

              {brief && (
                <article className={`wmcp-brief-result ${brief.verdict}`}>
                  <header>
                    <span className="wmcp-verdict">{brief.verdict.replace(/_/g, " ")}</span>
                    <strong>{brief.headline}</strong>
                    <code>{brief.briefing_id}</code>
                  </header>

                  <BriefGroup title="Read this first" items={brief.must_read} />
                  <BriefGroup title="Decisions that constrain it" items={brief.constraints} />
                  <BriefGroup title="It went wrong this way before" items={brief.prior_incidents} />
                  <BriefGroup title="Blast radius" items={brief.blast_radius} />
                  <BriefGroup title="Established procedure" items={brief.procedures} />

                  {brief.requires_approval.length > 0 && (
                    <div className="wmcp-brief-gate">
                      <strong>A person has to decide</strong>
                      <ul>
                        {brief.requires_approval.map((reason) => (
                          <li key={reason}>{reason}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <footer className="wmcp-brief-foot">
                    <p>
                      This opened a row in the outcome ledger. An agent closes it with{" "}
                      <code>record_orgmemory_outcome</code> once it knows whether the work
                      succeeded — that record, not the retrieval, is what compounds.
                    </p>
                    <Link href="/loop">See the outcome loop →</Link>
                  </footer>
                </article>
              )}
            </>
          )}
        </section>

        <section className="webmcp-console">
          <div className="webmcp-console-head">
            <div>
              <p className="webmcp-eyebrow">Reproducible memory handoff</p>
              <h2>Prove that the next agent starts ahead</h2>
            </div>
            <span className={`webmcp-ws-badge ${supported ? "on" : ""}`}>
              {supported === null
                ? "checking browser…"
                : supported
                  ? "WebMCP browser detected"
                  : "browser-native tools activate in /workspace"}
            </span>
          </div>

          {!user?.id && (
            <p className="webmcp-note">
              <Link href="/login">Sign in</Link> to run the live console against your workspace.
            </p>
          )}

          {user?.id && (
            <>
              {projects.length === 0 && (
                <p className="webmcp-note">Connect or create a memory space first.</p>
              )}

              {projects.length > 0 && !memoryReady && (
                <div className="webmcp-prep">
                  <div>
                    <strong>Prepare the demo space</strong>
                    <p>
                      Queue a small payments dataset (incidents, a decision, a dependency, a
                      procedure) as <em>proposals</em>. You approve them — that approval is the
                      human gate every agent works behind.
                    </p>
                  </div>
                  {isAdmin ? (
                    <button className="home-btn" onClick={() => void prepareDemoSpace()} disabled={preparing}>
                      {preparing ? "Queueing…" : "Queue demo proposals"}
                    </button>
                  ) : (
                    <small>An owner or admin must prepare the space.</small>
                  )}
                </div>
              )}

              {waitingOnHuman && (
                <div className="webmcp-approvals">
                  <div className="webmcp-approvals-head">
                    <strong>Waiting for a human decision — agents cannot approve</strong>
                    {isAdmin && (
                      <button className="home-btn" onClick={() => void approveAll()}>
                        Approve all {pendingProposals.length}
                      </button>
                    )}
                  </div>
                  <ul>
                    {pendingProposals.map((proposal) => (
                      <li key={proposal.id}>
                        <div>
                          <strong>[{proposal.kind}] {proposal.subject}</strong>
                          <em>{proposal.content}</em>
                          {proposal.reason && <small>Why: {proposal.reason}</small>}
                        </div>
                        {isAdmin && (
                          <button onClick={() => void approve(proposal)}>Approve</button>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="webmcp-runbar">
                <select
                  aria-label="Memory space"
                  value={activeSpace}
                  onChange={(event) => setSpaceId(event.target.value)}
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
                <button
                  className="home-btn"
                  onClick={() => void runSession("one")}
                  disabled={Boolean(running) || !activeSpace}
                >
                  {running === "one" ? "Agent is working…" : "Session 1 — agent investigates"}
                </button>
                {canRunTwo && (
                  <button
                    className="home-btn quiet"
                    onClick={() => void runSession("two")}
                    disabled={Boolean(running)}
                  >
                    {running === "two" ? "Agent is working…" : "Session 2 — brand-new agent"}
                  </button>
                )}
              </div>
              {note && <p className="webmcp-status">{note}</p>}
              {error && <p className="webmcp-error">{error}</p>}

              <div className="webmcp-sessions">
                <SessionPanel
                  lane="one"
                  label="Session 1"
                  sublabel="an agent seeing this workspace for the first time"
                  session={sessionOne}
                  running={running === "one"}
                  onApprove={isAdmin ? (proposal) => void approve(proposal) : undefined}
                />
                {(sessionTwo || running === "two") && (
                  <div className="webmcp-session-bridge" aria-hidden="true">
                    <span>human approved the proposal — knowledge is now in company memory</span>
                    <i>↓</i>
                    <strong>Session 2: a brand-new agent. No shared chat. No carried context.</strong>
                  </div>
                )}
                <SessionPanel
                  lane="two"
                  label="Session 2"
                  sublabel="a different agent, zero memory of Session 1 — it starts ahead anyway"
                  session={sessionTwo}
                  running={running === "two"}
                />
              </div>
            </>
          )}
        </section>

        <section className="webmcp-catalog wmcp-tool-command-center">
          <header>
            <div><p className="webmcp-eyebrow">Tool manifest</p><h2>What an agent discovers in the workspace</h2></div>
            <div className="wmcp-tool-filters" aria-label="Filter WebMCP tools">
              {(["all", "read-only", "governed"] as const).map((filter) => (
                <button key={filter} type="button" className={toolFilter === filter ? "active" : ""} onClick={() => setToolFilter(filter)}>{filter}</button>
              ))}
            </div>
          </header>
          <p className="webmcp-note">
            Registered through <code>document.modelContext.registerTool()</code> in the
            authenticated workspace. Search and retrieval run automatically; every
            <code>propose_*()</code> tool only queues a proposal.
          </p>
          <div className="wmcp-tool-list">
            {WEBMCP_TOOL_CATALOG.filter((tool) =>
              toolFilter === "all" ||
              (toolFilter === "read-only" ? tool.permission === "read-only" : tool.permission !== "read-only"),
            ).map((tool) => (
              <details key={tool.name}>
                <summary>
                  <span className={`wmcp-tool-permission ${tool.permission}`}>{tool.permission.replace(/-/g, " ")}</span>
                  <div><code>{tool.name}</code><strong>{tool.title}</strong></div>
                  <em>{tool.group}</em>
                </summary>
                <div className="wmcp-tool-detail">
                  <p>{tool.description}</p>
                  <section><span>Input schema</span><pre>{JSON.stringify(tool.inputSchema, null, 2)}</pre></section>
                  <section><span>Structured result example</span><pre>{JSON.stringify(tool.resultExample, null, 2)}</pre></section>
                  <section><span>Recent calls</span><strong>{recentActivity.filter((activity) => activity.tool === tool.name).length || "None in this page session"}</strong></section>
                </div>
              </details>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}

function SessionPanel({
  lane,
  label,
  sublabel,
  session,
  running,
  onApprove,
}: {
  lane: "one" | "two";
  label: string;
  sublabel: string;
  session?: AgentSession;
  running: boolean;
  onApprove?: (proposal: Proposal) => void;
}) {
  if (!session && !running) {
    return (
      <div className="webmcp-session empty" data-lane={lane}>
        <header>
          <strong>{label}</strong>
          <small>{sublabel}</small>
        </header>
        <p className="webmcp-note">Not run yet.</p>
      </div>
    );
  }
  return (
    <div className="webmcp-session" data-lane={lane} data-status={session?.status || "running"}>
      <header>
        <strong>{label}</strong>
        <small>{sublabel}</small>
        {session?.question && <code className="webmcp-q">“{session.question}”</code>}
        {session?.mode === "guided" && (
          <small className="webmcp-mode">
            model unreachable — guided run: the tools, evidence, and approval boundary are real;
            only the tool order is scripted
          </small>
        )}
      </header>

      {running && (
        <p className="webmcp-working">
          <span className="ws-working-dots" aria-hidden="true"><i /><i /><i /></span>
          discovering tools, calling memory…
        </p>
      )}
      {session?.error && <p className="webmcp-error">{session.error}</p>}

      <ol className="webmcp-trace">
        {(session?.steps || []).map((step, index) => (
          <li key={index} className="webmcp-step">
            <div className="webmcp-step-head">
              <span className="webmcp-step-n">{index + 1}</span>
              <code>{step.tool}()</code>
              {step.duration_ms != null && <small>{step.duration_ms} ms</small>}
            </div>
            {step.thought && <p className="webmcp-thought">{step.thought}</p>}
            <p className="webmcp-summary">{step.summary}</p>
          </li>
        ))}
      </ol>

      {session?.answer && session.status === "complete" && (
        <div className="webmcp-answer">
          <strong>Agent answer</strong>
          <p>{session.answer}</p>
          {session.memory_ids.length > 0 && (
            <div className="webmcp-cites">
              {session.memory_ids.map((id) => (
                <code key={id}>{id}</code>
              ))}
            </div>
          )}
        </div>
      )}

      {session?.proposal && (
        <div className="webmcp-proposal">
          <strong>The agent proposed new memory — nothing is saved yet</strong>
          <em>[{session.proposal.kind}] {session.proposal.subject}</em>
          <p>{session.proposal.content}</p>
          {onApprove ? (
            <button onClick={() => onApprove(session.proposal as Proposal)}>
              Approve into company memory
            </button>
          ) : (
            <small>Waiting for an admin to approve in the workspace.</small>
          )}
        </div>
      )}
    </div>
  );
}

function BriefGroup({ title, items }: { title: string; items: OrgMemoryBriefingCitation[] }) {
  // An empty group is omitted rather than shown empty: a briefing that lists
  // "Prior incidents: none" next to four that do have entries reads as
  // reassurance, and this page should never reassure by accident.
  if (!items.length) return null;
  return (
    <section className="wmcp-brief-group">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item.memory_id}>
            <div>
              <span className="wmcp-brief-kind">{item.type}</span>
              <strong>{item.subject}</strong>
            </div>
            <p>{item.content}</p>
            <code>{item.memory_id}</code>
          </li>
        ))}
      </ul>
    </section>
  );
}
