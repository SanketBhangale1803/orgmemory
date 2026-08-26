# Approvals and Agent Safety

Runbook does not only say what to do — it decides what an AI agent is
allowed to do. Every runbook step carries a typed `action_type`, and every
proposal is evaluated by the AgentGate adapter (AgentGate's real
`PolicyEngine` when importable, combined with Runbook's product policy).

## Action taxonomy and default policy

| Action type | Default decision |
|---|---|
| `read_only` | allowed |
| `analysis` | allowed |
| `draft_change` | allowed |
| `mutation` | approval required |
| `external_send` | approval required |
| `deployment` | approval required |
| `production_change` | admin approval required |
| `database_write` | approval required |
| `data_export` | approval required |
| `infra_change` | approval required |
| `customer_impacting_action` | approval required |
| `connector_access` | workspace admin approval if sensitive |
| `credential_access` | denied unless admin approval explicitly requested |
| anything unknown | fails closed (approval required) |

Any action in a production environment escalates to admin approval
regardless of type.

## Assertion reliability gate

An `OperationalAssertion` is a time-bounded, evidence-backed operational
claim (for example, that a runbook step applies to a service/configuration).
For production-changing proposals, `proposed`, `possibly_stale`, `stale`, or
`contradicted` assertions are not trusted. The proposal is escalated to admin
approval and records the assertion IDs and reason in its audit payload. A
dismissal is also audited, but does not silently turn stale evidence into a
trusted claim. This gate never executes a command or infrastructure change.

## Flow

```text
POST /api/actions/propose   → resolve real runbook step, render command
                              preview, evaluate policy, create action record
POST /api/actions/approve   → pending → approved (audited)
POST /api/actions/deny      → pending → denied (audited)
GET  /api/actions/pending   → approval queue
GET  /api/audit/actions     → action history
```

Approved actions remain **command previews**: this release ships no shell
executor, and `ALLOW_LOCAL_COMMAND_EXECUTION=false` is the default. The
`execution_mode` field says `would_execute` so nothing implies a command
ran.

## Inline approvals in the workspace

Decisions do not require a separate page. The workspace polls the approvals
queue and renders pending repository refresh requests directly beside the
conversation: who requested it (identity is carried with every request), why,
and approve/deny buttons for anyone whose role permits resolving it. Employees
see their own requests' status without buttons. A browser agent acting through
WebMCP can list pending approvals and record a decision through
`list_orgmemory_approvals` and `resolve_orgmemory_approval`, using exactly the
same authorized endpoints as the human buttons — the boundary is role- and
visibility-checked server-side either way.

The same loop starts at membership: a workspace owner adds people on the
account page; invited teammates land inside the workspace when they sign in,
raise refresh requests from their own sessions or agents, and admins decide
them inline.

## Operational memory approvals

Operational memories (`/api/projects/{id}/memories`) follow the same
philosophy: candidates are derived only from ingested evidence, stay
`proposed` until a human approves them, and approval writes provenance
edges (`OPERATIONAL_MEMORY_BACKED_BY`) to the graph.

## Audit

Proposals, approvals, denials, simulations, drift checks, memory decisions,
importer runs, and API-key lifecycle events are all recorded in
`audit_events` with actor, project, summary, and payload, and surfaced on
the Audit Log page.
