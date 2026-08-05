# OrgMemory

> The source-backed operating brain for your company.

OrgMemory learns how a company works from code, conversations, documents, tickets,
decisions, and uploaded knowledge. It turns that evidence into a living company
memory graph that employees and internal AI agents can query without asking people
to re-explain the company, repository, service, or prior decision.

## What OrgMemory is

OrgMemory is a company memory graph, not an incident tool, runbook generator, or generic chatbot over documents. It preserves distinct layers for raw sources, chunks, atomic `MemoryUnit` records, entities, profiles, and answer context. Every promoted memory cites a source; uncertain material remains a searchable chunk.

The primary workflow is:

```text
Raw company sources → ingestion → chunks → atomic memories → entity graph
→ company/project/repo/service profiles → HCAG context assembly → cited answer
```

The Company Brain loop is continuous rather than a one-time index:

```text
source revision → memory change set → current truth reconciliation
→ affected profiles/reports/skills → governed context envelope → agent
```

## Memory Work: from context to outcomes

OrgMemory now turns remembered company context into portable work packages for AI workers. The user describes an outcome once; HCAG selects the authorized scope, current memories, related entities, conflicts, and exact source evidence. OrgMemory then saves a revisioned brief and produces an `agent_packet` with an approval-aware execution plan.

```text
Outcome → authorized HCAG context → source-backed work package
→ human approval for consequential actions → connected worker
→ result evidence returned to company memory
```

This is complementary to broad AI coworker runtimes such as [OpenWorker](https://github.com/andrewyng/openworker): the worker owns the tool-execution loop, while OrgMemory owns organizational context, current truth, permissions, evidence, and durable outcome memory. OrgMemory does not copy OpenWorker and does not require it; the packet is portable through the API and MCP to any compatible worker.

## Why this is different from RAG

RAG retrieves passages. OrgMemory also extracts typed, scoped, temporally valid memories; connects them to entities and sources; tracks which memory updates or contradicts another; and assembles current profiles from atomic facts. Retrieval still uses the original evidence, so the graph does not become an unsupported summary layer.

## Product boundary

OrgMemory is organization-specific rather than a generic memory API: company,
project, repository, service, and person profiles; temporal validity; conflicts;
permission-aware retrieval; an inspectable company graph; and approval-aware work.
The web app is the starting point. Channels, IDEs, SDKs, CLI, and MCP are delivery
surfaces for the same governed brain.

## HCAG company memory engine

The HCAG adapter routes questions to company-memory domains such as project, policy, decision, ownership, temporal, deployment, and incident memory. It compiles context using this invariant:

```text
authorized team scope ∩ task relevance ∩ current truth
∩ entity graph neighborhood ∩ token budget
```

Each query activates a concurrent specialist swarm: hybrid sensory retrieval,
bounded graph traversal, and a current-truth historian. An immune-system critic
deduplicates their authorized evidence and records contradictions; one context
compiler creates the final token-bounded context. Domain specialists join for
API contracts, repository briefings, change history, and procedure validity.

Each answer persists both a `context_activation_runs` record and a
`ContextEnvelope` containing the principal, authorized teams, task, selected
memory/evidence, exact compiled context, active skill specs, source version
vector, token budget, expiry, and retrieval trace. This makes the dynamic
context given to an LLM or agent inspectable and reproducible. See
[`docs/CONTEXT_ACTIVATION_SWARM.md`](docs/CONTEXT_ACTIVATION_SWARM.md).

## Governed organizational scope

Workspaces can define hierarchical teams, team membership, and project grants. Sources may be shared with one or more teams; extracted memory inherits the source visibility boundary. Existing unscoped data remains workspace-visible for migration compatibility. Owners and admins can inspect the whole workspace, while member retrieval is security-trimmed before ranking and answer generation.

The invariant is strict: derived memory, context, briefs, and skills cannot be broader than their supporting source.

## Source-backed memory extraction

All ingestion paths—GitHub repositories, issues, pull requests, Slack, pasted knowledge, and uploaded files—store the raw item, chunk it, index the chunks, conservatively extract atomic memories, link each memory to its exact source/chunks in ArcadeDB, and reconcile current-memory relationships. Repository code is interpreted structurally: manifests, documented service tables, routes, configuration schemas, and docstrings can become memory, while CSS, JSX fragments, validation errors, and incomplete expressions remain evidence chunks and are never promoted as company policy.

Source provenance is enforced at ingestion. Repository evidence must match the selected project's GitHub repository; uploaded documents and Slack messages are explicitly assigned to one project and inherit its team scope. OrgMemory does not silently mix records from another repository or project.

`MemoryUnit` records contain workspace/project scope, type, subject, content, company/project/repo/service/person scope, source IDs, confidence, validity dates, and current status. Relationships include `UPDATES`, `EXTENDS`, `DERIVES`, `CONTRADICTS`, `SUPPORTS`, `MENTIONS`, `BELONGS_TO`, `OWNED_BY`, `DEPENDS_ON`, `DECIDED_BY`, `VALID_FOR`, and `INVALIDATED_BY`.

## Revisions, updates, and conflicts

Every stable source has immutable `SourceRevision` records. A changed revision produces a `MemoryChangeSet` that lists added, updated, invalidated, and conflicting memories. When new evidence changes a prior memory with the same subject, OrgMemory preserves both records, closes the prior validity window when appropriate, and adds an `UPDATES` or `CONTRADICTS` relationship. Removed claims are invalidated instead of silently disappearing.

Reports and briefs are versioned `Artifact` records linked to the exact source revisions, memories, and context envelope used to create them. A supporting change marks the artifact stale and creates a reviewable impact. Current policies and procedures can also be compiled into versioned `SkillSpec` files for agents; a relevant memory change marks the skill stale.

## Run locally

Start Docker Desktop first and wait until it reports that the engine is running.

```bash
cd ~/Desktop/startup/orgmemory
cp .env.example .env
make runbook
```

Open [http://localhost:3000](http://localhost:3000). API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs).

If `docker.sock` is missing, Docker Desktop is not running yet; start it and rerun `make runbook`.

Connect GitHub or Slack from **Sources**, or upload a document. Ingestion returns `memory_units_created` and the new memory IDs. Use **Memory Graph**, **Memories**, **Profiles**, **Updates**, **Conflicts**, and **Ask OrgMemory** to inspect and query the result.

Open **Memory Work**, select a project, and describe the desired outcome. Safe knowledge work produces a source-backed brief immediately. Slack work shows the exact editable message and destination at the top of the page; **Approve & post** sends it through Slack and stores the resulting permalink as evidence. Slack connections created before this feature must be reconnected once to grant `chat:write`.

Verified GitHub webhooks trigger an incremental repository reconciliation, including chunks, atomic memories, updates, conflicts, profiles, and HCAG retrieval state. After a Slack channel has been connected once, verified Slack message events add, update, or retire the corresponding project memories. Set `GITHUB_WEBHOOK_SECRET` and `SLACK_SIGNING_SECRET` and point the providers to `/api/webhooks/github` and `/api/webhooks/slack`.

Owners can use **Settings → Memory health** or `POST /api/projects/{project_id}/memory/repair` to re-run retained sources through the current extraction rules without altering the original evidence.

## API

Core memory endpoints:

```text
GET /api/memory/graph/summary
GET /api/memory/graph/nodes
GET /api/memory/graph/edges
GET /api/memory/units
GET /api/memory/units/{memory_id}
GET /api/memory/profiles/company
GET /api/memory/profiles/project/{project_id}
GET /api/memory/profiles/repo/{repo_id}
GET /api/memory/profiles/service/{service_name}
GET /api/memory/updates
GET /api/memory/conflicts
GET /api/memory/source-revisions
GET /api/memory/change-sets
GET /api/memory/artifacts
POST /api/memory/artifacts
GET /api/memory/skills
POST /api/memory/skills/compile
GET /api/memory/context/{envelope_id}
GET /api/memory/swarm/{run_id}
GET /api/models
GET /api/connectors/catalog
GET /api/workspaces/{workspace_id}/teams
POST /api/workspaces/{workspace_id}/teams
POST /api/teams/{team_id}/members
POST /api/projects/{project_id}/teams
POST /api/projects/{project_id}/memory/repair
POST /api/ask
POST /api/work
GET  /api/work
GET  /api/work/{work_id}
POST /api/work/{work_id}/steps/{step_id}/resolve
POST /api/work/{work_id}/steps/{step_id}/complete
```

Ask responses contain `answer`, `memory_profile_used`, `confidence`, `memory_units`, `evidence`, `related_entities`, `updates`, `conflicts`, `retrieval_trace`, and the persisted `context_envelope`. Answers are derived from authorized retrieved evidence. If evidence is insufficient, OrgMemory abstains.

## Python SDK and CLI

Install the typed SDK and its `orgmemory` command from this checkout:

```bash
make sdk-install
```

The client reads `ORGMEMORY_API_URL` and `ORGMEMORY_API_KEY`, or accepts them
explicitly:

```python
from orgmemory import OrgMemory

memory = OrgMemory(
    base_url="http://localhost:8000",
    api_key="om_live_...",
)
context = memory.ask(
    "prj_platform",
    "What changed in checkout, and why?",
    model="claude",
)

print(context.answer)
print(context.compiled_context)
```

The same package includes an operational CLI:

```bash
orgmemory health
orgmemory projects
orgmemory ask prj_platform "What changed in checkout, and why?" --model claude
orgmemory memories prj_platform
orgmemory graph prj_platform
orgmemory swarm swarm_01J... --json
```

Use `AsyncOrgMemory` for async applications. The public developer guide is
served at [http://localhost:3000/docs](http://localhost:3000/docs).

## MCP

Run `make mcp`. The preferred tools are:

```text
orgmemory_ingest_github_repo
orgmemory_ingest_slack_channel
orgmemory_upload_source
orgmemory_ask
orgmemory_search_memories
orgmemory_get_company_profile
orgmemory_get_project_profile
orgmemory_get_service_profile
orgmemory_get_memory_graph
orgmemory_list_memory_conflicts
orgmemory_list_memory_updates
orgmemory_list_source_revisions
orgmemory_list_change_sets
orgmemory_compile_skill
orgmemory_list_skills
orgmemory_create_work
orgmemory_list_work
orgmemory_get_work
orgmemory_resolve_work_step
orgmemory_complete_work_step
```

Legacy `runbook_*` MCP tools remain temporarily available for compatibility, but action policies, approvals, simulations, procedure extraction, and reliability review are advanced features and are not part of the default v1 navigation.

## Configuration

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
XAI_API_KEY=
KIMI_API_KEY=
ORG_MEMORY_DEFAULT_MODEL_PROVIDER=gpt
ORG_MEMORY_ENABLE_ACTIONS=false
ORG_MEMORY_ENABLE_PROCEDURES=false
ORG_MEMORY_ENABLE_ADVANCED_RELIABILITY=false
GITHUB_WEBHOOK_SECRET=
SLACK_SIGNING_SECRET=
```

Google, GitHub, passwordless email, and Slack configuration are documented in
`docs/OAUTH_SETUP.md`. Secrets are encrypted at rest, source access is
workspace-scoped, and API keys are workspace-bound.

## Tests

```bash
make test
make sdk-test
npm --prefix frontend test
```

Grounding tests verify that the same question over different sources produces different answers, confident answers require evidence, insufficient evidence abstains, and no service-specific canned response exists.

## Known limitations

- Extraction is deliberately conservative and primarily deterministic; GPT,
  Claude, Gemini, Grok, or Kimi may synthesize answers but cannot promote
  unsupported memory.
- GitHub, Slack, uploads, API, Python, CLI, and MCP are live. Google Workspace,
  Gmail, Microsoft 365, Teams, Outlook, and Atlassian remain adapter work.
- Conflict matching currently relies on normalized subjects; entity-assisted and model-assisted reconciliation can improve this.
- Profiles are assembled on read from current memories rather than materialized incrementally.
- Team grants are project/source scoped; field-level classification and external identity-group sync are not implemented yet.
- Legacy advanced routes remain in the codebase for backward compatibility.

## Migration note

Runbook was the previous product direction. OrgMemory is now focused on the
company brain rather than operational runbooks. Legacy database table names and
environment variables remain temporarily for migration compatibility.
