# Runbook Architecture

Runbook keeps four boundaries explicit: connector acquisition, normalized
ingestion, graph-backed retrieval, and governed action execution. Connector
credentials never enter knowledge chunks. Raw source content is retained in
application state (SQLite), while relationships and retrieval memory are
written through the `GraphStore` contract to ArcadeDB.

```text
GitHub / Slack / uploads / logs / importers
                  │
                  ▼
     IngestionService (normalize, chunk, extract services/signals)
                  │
          ┌───────┴────────┐
          ▼                ▼
   HCAG adapter        ArcadeDB graph
   (route, windows)    (46 vertex / 54 edge types)
          └───────┬────────┘
                  ▼
        graph_ranker (hybrid lexical/service/source ranking)
                  │
        reasoner (evidence-only; LLM optional) + trust scoring
                  │
   intelligence layer: correlation · drift · simulation · blast radius
                  │
        RunbookService (versioned, cited YAML/JSON)
                  │
     OperationalAssertion + ChangeImpactService
                  │
        AgentGate policy → approvals → audit
```

## Components

- **`app/core`** — settings, SQLite schema (projects, users, workspaces,
  sessions, knowledge items, runbooks, actions, audit events, connector
  accounts, ingestion jobs, operational memories, API keys).
- **`app/graph`** — `GraphStore` interface, ArcadeDB HTTP implementation,
  in-memory implementation for tests, idempotent migrations,
  `graph_ranker` (single ranking implementation shared by both stores),
  `graph_explainer` (edge tuples → readable paths), graph builder used by
  repository ingestion.
- **`app/ingestion`** — one `ingest_item` path for every source type;
  repository scanner (files, imports, endpoints, env vars, compose,
  workflows, Jenkinsfiles, issues, PRs); Slack ingestor; job records.
- **`app/hcag_adapter`** — imports HCAG's `QueryPlanner` when available with
  a deterministic fallback; routes queries; persists `ContextWindow`
  vertices via `arcadedb_window_store`; builds retrieval traces.
- **`app/retrieval`** — ask pipeline: route → retrieve → rank → reason from
  evidence only → cite → trust-score → correlate recent changes for
  incident questions. Insufficient evidence returns the explicit refusal.
- **`app/intelligence`** — trust scoring, drift detection,
  change-to-incident correlation, simulation, blast radius. Every module
  states its evidence basis (e.g. `recency_basis: ingestion_time`).
- **`app/memory`** — operational memories derived only from ingested
  evidence, approval-gated, provenance edges in the graph.
- **`app/runbooks`** — extraction of versioned, cited runbooks with typed
  steps, approval rules, trust score, graph trace, drift status.
- **`app/reliability`** — `OperationalAssertion` lifecycle state in SQLite,
  graph-backed provenance in ArcadeDB, and `ChangeImpactService`. It compares
  retained GitHub/re-ingestion file and version metadata to existing graph
  edges, creates actionable review reports, and labels conclusions as
  code/config evidence rather than runtime proof.
- **`app/agentgate_adapter` + `app/approvals`** — AgentGate's real policy
  engine combined with Runbook's action taxonomy; proposals, approvals,
  denials, audit. No shell executor ships.
- **`app/importers`** — incident-tool migration interfaces (PagerDuty live;
  others scaffolded, honestly `not_connected`).
- **`mcp_server`** — FastMCP stdio server; 15 tools calling the HTTP API.
- **`frontend`** — Next.js app router, custom design system.

## Design rules

1. HCAG owns routing and context-window selection; Runbook owns the
   ArcadeDB persistence adapter. Evidence ranking requires exact token or
   service matches before source-quality boosts apply.
2. Answer generation receives only ranked evidence; every supported
   response returns the chunks it used.
3. Runbook extraction is downstream of retrieval: a generated procedure
   cannot exist without evidence-backed procedures or commands, and each
   persisted runbook links back to its `KnowledgeItem` sources.
4. AgentGate evaluates typed steps after parameter rendering and before any
   execution boundary; the current release records command previews and
   never invokes a shell.
5. Graph unavailability degrades with explicit errors; nothing fabricates
   counts or relationships.
6. Time claims are labeled: local corpora only have ingestion time, and
   trust/drift/correlation say so.
7. A source change is a reason to verify an assertion, never automatic proof
   that a procedure is invalid. Unresolved assertions cannot be trusted by a
   production-changing action proposal; the existing AgentGate boundary
   escalates it to admin review.
