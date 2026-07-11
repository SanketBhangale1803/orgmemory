# Runbook Reliability

Runbook treats a procedure as a set of operational claims with provenance,
not as permanently correct text. An `OperationalAssertion` has a subject
(service, file, environment variable, config key, runbook step, or command),
source evidence, version/commit metadata when available, affected runbooks,
an environment scope, an owner if explicitly known, and an auditable review
state.

## Workflow

1. Extracting a cited runbook creates proposed assertions for its steps.
2. GitHub PR metadata or repository re-ingestion identifies changed files and
   their graph-connected services, config keys, variables, commands, and
   workflows.
3. `ChangeImpactService` follows real graph edges to assertions, runbooks, and
   steps. It writes an actionable impact report with source evidence, graph
   connection, owner, severity, and recommended review action.
4. A reviewer verifies, marks stale, supersedes, or dismisses an assertion.
   Stale, supersede, and dismiss require a rationale. Every decision records
   actor, time, before/after status, and evidence context in the audit log.
5. AgentGate consults linked assertion state for production-changing actions.
   Unresolved assertions force admin review and are never presented as trusted
   support for an action.

## Status meanings

| Status | Meaning |
| --- | --- |
| `proposed` | Extracted from evidence but not yet human-verified. |
| `verified` | A human verified it against current cited evidence. |
| `possibly_stale` | Connected source evidence changed; review is required. |
| `stale` | A reviewer determined the claim should not be relied upon. |
| `contradicted` | Current evidence conflicts with the claim. |
| `superseded` | Replaced by a newer claim or procedure. |

## Evidence limits and scope

An impact report distinguishes a direct graph connection from an inferred
runbook/service overlap. In both cases, source change is evidence to verify;
it is not proof a procedure is invalid. Current v1 uses retained repository
and GitHub PR/commit metadata only. Runtime telemetry is explicitly shown as
`not_connected`; Runbook does not fabricate Datadog, Kubernetes, Jira, Slack
notification, or other observability integrations. This release also retains
the no-execution constraint: approvals and simulations are previews only.
