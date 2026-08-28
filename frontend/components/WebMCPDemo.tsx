"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";
import { ORGMEMORY_WEBMCP_TOOLS } from "@/lib/webmcp";

/* The console runs a REAL agent (the workspace's configured model) over the
   page's WebMCP tool surface. Session 1 investigates and proposes; a human
   approves; Session 2 is a brand-new agent with zero conversation memory that
   answers only because the previous agent's verified knowledge is now in
   OrgMemory. That handoff is the product. */

const DEMO_PROJECT_NAME = "WebMCP Demo";
const DEMO_SERVICE = "payments";

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
    <div className="webmcp-page">
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
          <p className="webmcp-eyebrow">The memory layer for browser agents</p>
          <h1>Agents that remember your company — and each other</h1>
          <p className="webmcp-lede">
            Every AI agent session starts from zero. This page registers OrgMemory as a
            browser-native Model Context Provider, so any agent can search what the company
            already knows — and, after a human approves it, leave verified knowledge behind for
            the <em>next</em> agent.
          </p>
          <div className="webmcp-flow" aria-label="How it works">
            <span>agent discovers OrgMemory</span>
            <i aria-hidden="true">→</i>
            <span>searches company history with tools</span>
            <i aria-hidden="true">→</i>
            <span>answers with evidence</span>
            <i aria-hidden="true">→</i>
            <span>proposes what it learned</span>
            <i aria-hidden="true">→</i>
            <span>human approves</span>
            <i aria-hidden="true">→</i>
            <span>the next agent starts ahead</span>
          </div>
          <p className="webmcp-boundary">
            <strong>Capability is not authorization.</strong> Search is read-only and
            permission-trimmed on the server. The only write an agent can make is a proposal —
            and everything an agent reads is data, never instructions.
          </p>
        </section>

        <section className="webmcp-console">
          <div className="webmcp-console-head">
            <div>
              <p className="webmcp-eyebrow">Live agent console</p>
              <h2>Watch a real agent use company memory</h2>
            </div>
            <span className={`webmcp-ws-badge ${supported ? "on" : ""}`}>
              {supported === null
                ? "checking browser…"
                : supported
                  ? "WebMCP browser detected"
                  : "register via document.modelContext on /workspace"}
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

        <section className="webmcp-catalog">
          <h2>What an agent discovers on this page</h2>
          <p className="webmcp-note">
            Registered through <code>document.modelContext.registerTool()</code> in the
            authenticated workspace. Search and retrieval run automatically; every
            <code>propose_*()</code> tool only queues a proposal.
          </p>
          <ul>
            {ORGMEMORY_WEBMCP_TOOLS.map((tool) => (
              <li key={tool}>
                <code>{tool}()</code>
              </li>
            ))}
          </ul>
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
