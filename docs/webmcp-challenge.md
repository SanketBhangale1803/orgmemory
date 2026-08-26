# WebMCP Challenge implementation record

OrgMemory existed before the WebMCP Challenge. This record separates the stable
product baseline from the browser-native work added during the challenge.

## Pre-challenge baseline

- Baseline commit: `4b3ec3c` (`chore: freeze pre-WebMCP baseline`)
- Baseline tag: `pre-webmcp-2026-08-25`
- Baseline date: August 25, 2026
- Validation at the boundary: 231 backend tests passed, one deliberate live-LLM
  contract test skipped, 11 frontend tests passed, 5 SDK tests passed, Ruff,
  Black, TypeScript, the Next.js production build, Docker health, and ArcadeDB
  graph checks passed.

Before the challenge, OrgMemory already provided source-backed organizational
memory, permission-scoped retrieval, an authenticated Next.js workspace, REST
and Python clients, and a separate HTTP/stdio MCP server. That MCP server did
not expose tools from the web page through `document.modelContext`.

## Work added during the challenge

Phase 1 turns the authenticated workspace into a browser-native Model Context
Provider. The page registers these read-only tools:

1. `list_orgmemory_spaces` lists only the projects visible to the signed-in user.
2. `ask_orgmemory` asks permission-scoped company memory, returns source citations,
   and renders the same answer in the visible workspace conversation.
3. `inspect_orgmemory_changes` summarizes additions, updates, invalidations,
   conflicts, and affected artifacts from recent memory change sets.

Phase 2 adds one deliberately approval-gated write path:

4. `propose_repository_refresh` creates a deduplicated request to refresh a
   GitHub-backed memory space when the current evidence is stale or incomplete.
   It cannot run an import itself. The request appears in **Approvals**, where a
   signed-in person must explicitly approve or deny it. Only approval queues the
   server-side GitHub ingest and records its outcome in the audit trail.

The implementation is in `frontend/lib/webmcp.ts`, with lifecycle management in
`frontend/hooks/useOrgMemoryWebMCP.ts` and the human-agent interaction in
`frontend/components/WorkspaceChat.tsx`.

## Security boundary

- Tools register only inside the authenticated workspace.
- Calls reuse the page's HttpOnly session cookie through the existing API client;
  browser agents never receive credentials.
- Project IDs are checked against the signed-in user's already authorized project
  list before a scoped API call is made.
- Phase 1 tools are read-only and explicitly annotated as non-destructive.
- The Phase 2 tool is annotated as a non-destructive, approval-required write:
  proposing is idempotent, has no repository side effect, and returns the next
  human step instead of pretending that a refresh happened.
- Refresh requests are tied to the authorized project, workspace, requester,
  and normalized reason. The approvals list is project-visibility filtered, and
  resolving a request rechecks project write permission.
- The actual GitHub ingest runs only after approval, records success or failure,
  and keeps credentials server-side in the existing connector secret store.
- An `AbortController` removes tools when the page unmounts or the authorized
  project set changes.
- Ordinary browsers without WebMCP continue to work through feature detection.

## Judge walkthrough

Open the live OrgMemory workspace in ChatGPT's in-app browser or Chrome with
WebMCP enabled, then ask the browser agent:

1. "What OrgMemory spaces can I access?"
2. "Using OrgMemory, what changed recently in the selected project?"
3. "Ask OrgMemory what I should know before editing this service."
4. When evidence is missing, ask: "Propose refreshing this repository because
   the recent changes have not been indexed." Confirm that the agent reports a
   pending request, then open **Approvals**. The repository must remain untouched
   until a person presses **Approve & refresh**.

The agent should discover the four page tools, use the project IDs returned by
the first tool, and place source-backed answers in both its response and the
visible OrgMemory conversation. The one write-capable tool must never bypass the
human approval boundary.
