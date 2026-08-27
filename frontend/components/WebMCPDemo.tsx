"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";
import { ORGMEMORY_WEBMCP_TOOLS } from "@/lib/webmcp";

/* The demo dataset. Every entry becomes a memory proposal first: the demo
   deliberately makes you press Approve, because that human decision is the
   product boundary being demonstrated. */
const DEMO_SEEDS = [
  {
    kind: "incident",
    subject: "payments outage: PostgreSQL connection-pool exhaustion",
    content:
      "Payments failed for 40 minutes. Connection pool on the shared PostgreSQL cluster was exhausted; worker concurrency in the payments deployment had been raised the day before. Resolved by rolling concurrency back and restarting the pool.",
    service: "payments",
    reason: "Post-mortem was reviewed and published by the platform team.",
  },
  {
    kind: "incident",
    subject: "payments degraded checkout timeouts",
    content:
      "Checkout latency spiked and requests timed out. Payments worker pool exhaustion during the nightly batch job starved the checkout path. Mitigated by moving the batch job off business hours.",
    service: "payments",
    reason: "Confirmed in the incident channel and linked monitoring dashboard.",
  },
  {
    kind: "decision",
    subject: "cap payments worker concurrency",
    content:
      "The team decided to cap payments worker concurrency to protect the shared PostgreSQL connection pool instead of per-service pools.",
    service: "payments",
    reason: "Recorded decision from the platform architecture review.",
  },
  {
    kind: "dependency",
    subject: "payments depends on the shared PostgreSQL cluster",
    content:
      "Payments shares the PostgreSQL cluster with the ledger service; pool exhaustion on either affects the other.",
    service: "payments",
    reason: "Confirmed against the deployment manifest and service owner.",
  },
  {
    kind: "fact",
    subject: "payments owned by the Payments Platform team",
    content: "Payments is owned by the Payments Platform team; escalation starts with the on-call engineer.",
    service: "payments",
    reason: "Ownership page is current.",
  },
  {
    kind: "procedure",
    subject: "payments pool exhaustion first response",
    content:
      "1) Check the PostgreSQL connection count dashboard. 2) Compare active worker concurrency against the configured cap. 3) Restart the payments pool if saturation holds. 4) Page the Payments Platform on-call if the cap itself was raised.",
    service: "payments",
    reason: "Validated during the last two incidents.",
  },
] as const;

/* A stand-in for the "other WebMCP-enabled apps" a real agent would query —
   GitHub, a monitoring system, an issue tracker. Clearly labelled as
   simulated so the demo never pretends to have live integrations it has. */
const SIMULATED_LIVE_CONTEXT = [
  {
    tool: "github.deployments (simulated)",
    finding: "Deployment 2 hours ago changed worker_concurrency from 8 to 32 in payments.",
  },
  {
    tool: "monitoring.metrics (simulated)",
    finding: "PostgreSQL active connections pinned at max_connections for 38 minutes.",
  },
] as const;

type Project = { id: string; name: string; repository?: string };
type Unit = {
  id: string;
  project_id: string;
  project_name?: string;
  type: string;
  subject: string;
  content: string;
  scope?: { service?: string };
  score?: number;
};
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

type Step = {
  tool: string;
  what: string;
  result: string;
  detail?: string[];
};

const DEMO_PROJECT_NAME = "WebMCP Demo";
const DEMO_SERVICE = "payments";

export default function WebMCPDemo() {
  const [user, setUser] = useState<any>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [demoProject, setDemoProject] = useState<Project | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [phase, setPhase] = useState<
    "idle" | "creating" | "seeding" | "ready" | "running" | "proposing" | "done"
  >("idle");
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [supported, setSupported] = useState<boolean | null>(null);

  const isAdmin = user?.role === "owner" || user?.role === "admin";
  const loaded = useMemo(() => Boolean(user), [user]);

  useEffect(() => {
    setSupported(typeof document !== "undefined" && Boolean(document.modelContext));
    api<any>("/api/auth/me")
      .then(setUser)
      .catch(() => setUser({}));
    api<Project[]>("/api/projects")
      .then((items) => {
        setProjects(items);
        setDemoProject(items.find((item) => item.name === DEMO_PROJECT_NAME) || null);
      })
      .catch(() => undefined);
  }, []);

  const search = useCallback(
    async (projectId: string, query: string, type?: string, limit = 10): Promise<Unit[]> => {
      const params = new URLSearchParams();
      if (query) params.set("q", query);
      if (projectId) params.set("project_id", projectId);
      if (type) params.set("type", type);
      params.set("limit", String(limit));
      const response = await api<{ results: Unit[] }>(`/api/memory/search?${params}`);
      return response.results || [];
    },
    [],
  );

  async function createDemoSpace() {
    setError("");
    setPhase("creating");
    try {
      if (demoProject) {
        // Space already exists (a previous demo run) — just queue the dataset.
        await seedMemories(demoProject.id);
        return;
      }
      const created = await api<Project>("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name: DEMO_PROJECT_NAME }),
      });
      setDemoProject(created);
      await seedMemories(created.id);
    } catch (e: any) {
      setError(e.message);
      setPhase("idle");
    }
  }

  /* Proposals only — nothing enters memory until a person presses Approve. */
  async function seedMemories(projectId: string) {
    setPhase("seeding");
    const seeded: Proposal[] = [];
    for (const seed of DEMO_SEEDS) {
      seeded.push(
        await api<Proposal>("/api/memory/proposals", {
          method: "POST",
          body: JSON.stringify({ project_id: projectId, ...seed }),
        }),
      );
    }
    setProposals((current) => {
      const known = new Set(current.map((proposal) => proposal.id));
      return [...current, ...seeded.filter((proposal) => !known.has(proposal.id))];
    });
    setNote(
      "The demo dataset is queued as proposals. Approve them below — that approval step is the whole safety model.",
    );
    setPhase("ready");
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
    for (const proposal of proposals.filter((item) => item.status === "pending_approval")) {
      await approve(proposal);
    }
    setNote("All demo memories approved — they are now searchable company memory.");
  }

  async function runIncidentDemo() {
    if (!demoProject) return;
    setError("");
    setPhase("running");
    const collected: Step[] = [];

    const incidentUnits = await search(demoProject.id, DEMO_SERVICE, "incident", 20).catch(
      () => [] as Unit[],
    );
    collected.push({
      tool: "get_incidents(service: payments)",
      what: "Search company memory for previous payments incidents.",
      result: incidentUnits.length
        ? `${incidentUnits.length} previous incident${incidentUnits.length === 1 ? "" : "s"} found.`
        : "No incidents remembered yet — approve the demo proposals first.",
      detail: incidentUnits.map(
        (unit) => `[${unit.type}] ${unit.subject} — ${unit.content}`,
      ),
    });

    const decisionUnits = await search(demoProject.id, "concurrency pool", "decision", 5).catch(
      () => [] as Unit[],
    );
    collected.push({
      tool: "get_decisions(project: WebMCP Demo)",
      what: "Retrieve related architecture decisions.",
      result: decisionUnits.length
        ? `${decisionUnits.length} decision${decisionUnits.length === 1 ? "" : "s"} found.`
        : "No decisions remembered yet.",
      detail: decisionUnits.map((unit) => `${unit.subject} — ${unit.content}`),
    });

    const dependencyUnits = await search(demoProject.id, DEMO_SERVICE, "dependency", 10).catch(
      () => [] as Unit[],
    );
    collected.push({
      tool: "get_dependencies(service: payments)",
      what: "Retrieve remembered service dependencies for blast-radius reasoning.",
      result: dependencyUnits.length
        ? `${dependencyUnits.length} remembered dependenc${dependencyUnits.length === 1 ? "y" : "ies"}.`
        : "No dependencies remembered yet.",
      detail: dependencyUnits.map((unit) => `${unit.subject} — ${unit.content}`),
    });

    collected.push({
      tool: "get_runbook(service: payments, issue: pool exhaustion)",
      what: "Retrieve the runbook the org already validated for this failure mode.",
      result:
        "No runbook is remembered for this space. Runbooks are extracted from ingested sources — the demo dataset records the procedure as memory instead.",
      detail: DEMO_SEEDS.filter((seed) => seed.kind === "procedure").map(
        (seed) => `${seed.subject} — ${seed.content}`,
      ),
    });

    collected.push({
      tool: "other WebMCP-enabled apps (simulated here)",
      what: "A real agent now combines OrgMemory history with live context from other WebMCP tools: GitHub, monitoring, issue trackers.",
      result: SIMULATED_LIVE_CONTEXT.length
        ? `${SIMULATED_LIVE_CONTEXT.length} live signals compared against ${incidentUnits.length} remembered incidents.`
        : "No live signals.",
      detail: SIMULATED_LIVE_CONTEXT.map((signal) => `${signal.tool}: ${signal.finding}`),
    });

    collected.push({
      tool: "agent answer (evidence-grounded)",
      what: "The agent answers from history + live context, citing its evidence.",
      result:
        incidentUnits.length >= 2
          ? "The current symptoms match two previous incidents caused by PostgreSQL connection-pool exhaustion. A recent deployment also changed worker concurrency, which makes this the most likely cause."
          : "Not enough remembered evidence yet — approve the demo proposals and rerun.",
      detail: [
        "Evidence: remembered incidents + decisions + dependencies (OrgMemory WebMCP)",
        "Evidence: deployment record and metrics (other WebMCP apps, simulated here)",
      ],
    });

    setSteps(collected);
    setPhase("proposing");
  }

  async function proposeTodaysIncident() {
    if (!demoProject) return;
    setError("");
    try {
      const proposal = await api<Proposal>("/api/memory/proposals", {
        method: "POST",
        body: JSON.stringify({
          project_id: demoProject.id,
          kind: "incident",
          subject: "payments outage recurrence: connection-pool exhaustion",
          content:
            "Symptoms matched the two previous pool-exhaustion incidents. A deployment 2 hours prior raised worker concurrency; PostgreSQL connections pinned at max_connections. Diagnosis verified against monitoring before recording.",
          service: DEMO_SERVICE,
          reason: "Diagnosis was verified against live monitoring before this proposal.",
        }),
      });
      setProposals((current) => [...current, proposal]);
      setPhase("done");
      setNote(
        "The agent proposed today's incident as a memory proposal. It is NOT saved yet — approve it below and it becomes searchable company memory.",
      );
    } catch (e: any) {
      setError(e.message);
    }
  }

  const pendingCount = proposals.filter((item) => item.status === "pending_approval").length;
  const approvedCount = proposals.filter((item) => item.status === "approved").length;

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
          <p className="webmcp-eyebrow">Browser-native Model Context Provider</p>
          <h1>Organizational memory for browser AI agents</h1>
          <p className="webmcp-lede">
            This workspace registers itself with WebMCP-capable browsers, so an AI agent can
            discover company memory as tools and call them directly — instead of scraping pages
            or clicking through the UI.
          </p>
          <div className="webmcp-flow" aria-label="How it works">
            <span>Browser AI</span>
            <i aria-hidden="true">→</i>
            <span>discovers OrgMemory WebMCP</span>
            <i aria-hidden="true">→</i>
            <span>searches organizational history</span>
            <i aria-hidden="true">→</i>
            <span>combines it with live system context</span>
            <i aria-hidden="true">→</i>
            <span>answers with evidence</span>
          </div>
          <p className="webmcp-boundary">
            <strong>Capability is not authorization.</strong> Read-only tools run automatically;
            every write is a proposal that waits for an explicit human decision; and anything an
            agent reads is treated as data, never as instructions.
          </p>
        </section>

        <section className="webmcp-catalog">
          <h2>What an agent can call</h2>
          <p>
            {supported === null
              ? "Checking this browser…"
              : supported
                ? "This browser exposes document.modelContext. Open the workspace and the tools below register live."
                : "This browser does not expose document.modelContext yet — the tools below still describe what agents get in a WebMCP-capable browser."}
          </p>
          <ul>
            {ORGMEMORY_WEBMCP_TOOLS.map((tool) => (
              <li key={tool}>
                <code>{tool}()</code>
              </li>
            ))}
          </ul>
          <p className="webmcp-note">
            Search and retrieval are read-only. Every <code>propose_*()</code> tool only queues a
            proposal — company memory changes only after a person approves it, on this page or in
            the workspace rail.
          </p>
        </section>

        <section className="webmcp-demo">
          <h2>Prove it: &ldquo;Why is the payments service failing again?&rdquo;</h2>
          {!loaded && <p>Checking your session…</p>}
          {loaded && !user?.id && (
            <p>
              <Link href="/login">Sign in</Link> to run the demo against your own workspace.
            </p>
          )}
          {user?.id && (
            <>
              <ol className="webmcp-steps" aria-label="Demo progress">
                <li className={phase === "idle" || phase === "creating" || phase === "seeding" ? "active" : ""}>
                  {!demoProject ? (
                    isAdmin ? (
                      <button
                        className="home-btn"
                        onClick={() => void createDemoSpace()}
                        disabled={phase !== "idle"}
                      >
                        {phase === "creating" || phase === "seeding"
                          ? "Preparing…"
                          : "Step 1 — create the demo memory space"}
                      </button>
                    ) : (
                      <span>
                        An owner or admin must create the &ldquo;{DEMO_PROJECT_NAME}&rdquo; space
                        first.
                      </span>
                    )
                  ) : (
                    <span>
                      Demo space ready: <strong>{demoProject.name}</strong>
                      {!proposals.length && isAdmin && (
                        <button
                          className="home-btn"
                          onClick={() => void createDemoSpace()}
                          disabled={phase !== "idle"}
                        >
                          {phase === "seeding" ? "Queueing…" : "Load the demo dataset"}
                        </button>
                      )}
                    </span>
                  )}
                </li>
                <li className={phase === "ready" ? "active" : ""}>
                  {proposals.length
                    ? `${approvedCount}/${proposals.length} demo memories approved — ${pendingCount} waiting`
                    : "Step 2 — approve the demo memories (a human decision, always)"}
                </li>
                <li className={phase === "running" || steps.length ? "active" : ""}>
                  Step 3 — run the incident walkthrough
                  {demoProject && (
                    <button
                      className="home-btn"
                      onClick={() => void runIncidentDemo()}
                      disabled={phase === "running"}
                    >
                      {phase === "running" ? "Searching memory…" : "Run the walkthrough"}
                    </button>
                  )}
                </li>
              </ol>

              {pendingCount > 0 && (
                <div className="webmcp-approvals">
                  <div className="webmcp-approvals-head">
                    <strong>Waiting for a human decision</strong>
                    {isAdmin && (
                      <button className="home-btn" onClick={() => void approveAll()}>
                        Approve all {pendingCount}
                      </button>
                    )}
                  </div>
                  <ul>
                    {proposals
                      .filter((proposal) => proposal.status === "pending_approval")
                      .map((proposal) => (
                        <li key={proposal.id}>
                          <div>
                            <strong>[{proposal.kind}] {proposal.subject}</strong>
                            <em>{proposal.content}</em>
                            {proposal.reason && <small>Why: {proposal.reason}</small>}
                          </div>
                          {isAdmin ? (
                            <button onClick={() => void approve(proposal)}>Approve</button>
                          ) : (
                            <small>needs an admin</small>
                          )}
                        </li>
                      ))}
                  </ul>
                </div>
              )}

              {steps.length > 0 && (
                <div className="webmcp-trace">
                  {steps.map((step, index) => (
                    <article key={index}>
                      <header>
                        <code>{step.tool}</code>
                        <span>{step.what}</span>
                      </header>
                      <p>{step.result}</p>
                      {step.detail && step.detail.length > 0 && (
                        <ul>
                          {step.detail.map((line, lineIndex) => (
                            <li key={lineIndex}>{line}</li>
                          ))}
                        </ul>
                      )}
                    </article>
                  ))}
                </div>
              )}

              {phase === "proposing" && (
                <button className="home-btn" onClick={() => void proposeTodaysIncident()}>
                  Final step — let the agent propose today&rsquo;s incident
                </button>
              )}

              {phase === "done" && (
                <p className="webmcp-loop">
                  Loop closed: the agent proposed verified knowledge, you approved it, and the
                  next agent that asks about payments will find it. That is OrgMemory —
                  <strong> memory with a human boundary.</strong>
                </p>
              )}

              {note && <p className="webmcp-status">{note}</p>}
              {error && <p className="webmcp-error">{error}</p>}
            </>
          )}
        </section>
      </main>
    </div>
  );
}
