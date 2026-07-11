# Runbook Extraction

`POST /api/runbooks/extract` turns retrieved evidence into an executable,
versioned procedure. Extraction is downstream of retrieval: if the ranked
evidence contains no procedures or commands, the response is honestly
`runbooks_created: 0` with the reason.

## Pipeline

```text
query → HCAG route → retrieve evidence → extract procedures/commands
      → classify step action types → derive approval rules and risk
      → compute trust score and graph trace → version → persist
```

## Runbook shape

```yaml
id: handle_reddit_service_kafka_failure_recovery
name: Reddit Service Kafka Failure Recovery
description: Evidence-backed procedure extracted for ...
domain: engineering_operations
subdomain: incident_response
services: [reddit_service]
triggers: [reddit_service, kafka, "...error lines from evidence..."]
required_context: [target service, target environment, current logs and configuration]
steps:
  - id: step_1
    description: Inspect reddit_service logs with docker logs reddit_service.
    action_type: read_only
    approval_required: false
    command_template: docker logs reddit_service
  - id: step_2
    description: Restart reddit_service with docker restart reddit_service.
    action_type: mutation
    approval_required: true
    command_template: docker restart reddit_service
approval_rules:
  - { action_type: mutation, requires: human_approval }
risk_level: medium
sources:            # every runbook cites its evidence
  - { item_id: item_..., type: incident, title: ..., url: ..., snippet: ... }
graph_trace:        # readable graph paths from the retrieval
  - "chunk_ab12 —CHUNK_REFERENCES_SERVICE→ reddit_service"
trust_score: { score: 0.71, level: medium, reason: "...", factors: {...} }
drift_status: fresh
version: 1
versions: [{ version: 1, updated_at: ..., confidence: 0.78 }]
confidence: 0.78
```

## Versioning

Re-extraction with identical steps/sources/services/triggers keeps the
version; any content change bumps it and appends to `versions`. Files are
written to `generated_runbooks/{project_id}/{key}.{yaml,json}` and the
graph gets `Runbook`, `RunbookStep`, `RUNBOOK_USES_SOURCE`,
`RUNBOOK_APPLIES_TO_SERVICE`, and `RUNBOOK_HAS_STEP` records.

## Drift

`GET /api/runbooks/{id}/drift` (or per-project `GET /api/projects/{id}/drift`)
re-checks every cited source against current knowledge. Signals:

| Signal | Severity |
|---|---|
| `source_missing` — cited item no longer exists | stale |
| `source_changed` — same source re-ingested without the cited passage | possibly_stale |
| `service_missing` — service gone from the graph | stale |
| `newer_error_evidence` — new error evidence about the runbook's services | needs_human_review |
| `conflicting_evidence` — current cause statements contradict | conflicting_evidence |

The runbook's `drift_status` is the worst signal severity; low-confidence
runbooks default to `needs_human_review`. Signals are persisted as
`RunbookDriftSignal` vertices.

## Simulation

`POST /api/simulate` dry-runs a runbook (chosen explicitly or matched from
a scenario like "Simulate Kafka outage for reddit_service") through the
same AgentGate policy as live proposals: per-step decision, approval role,
risk score, unresolved parameters, dangerous steps, and what evidence is
needed before execution. Nothing executes and no approval records are
created.
