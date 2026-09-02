# OrgMemory — WebMCP Challenge demo script

Target runtime **2:52** (hard cap 3:00). ~400 words of voiceover at a deliberate
~140 wpm. Live URL shown on screen throughout: `orgmemory.vercel.app/webmcp`.

Optimized against the four judging criteria, in this order of screen time:
WebMCP Leverage (≈80% of runtime inside `document.modelContext`), Execution
(real product, real session boundary), Potential Impact (the outage it
prevents), Creativity (memory that outlives the session + the outcome ledger).

---

## Timed cut

| Time | Screen / action | Voiceover |
| --- | --- | --- |
| **0:00–0:15**<br>Cold open | A deployment console with a pending change: *raise worker concurrency, payments service*. Cursor hovers Deploy. Freeze. | Your company already knows why the payments service failed last time. It's in a postmortem nobody reads. So when an AI agent shows up to change that service, it starts from zero — and repeats the outage. |
| **0:15–0:35**<br>The surface | Cut to signed-in `orgmemory.vercel.app`. Open `/webmcp` command center: **21 tools · 14 read-only · 7 human-governed**. Split to DevTools console showing `document.modelContext.registerTool(...)` firing on page load. | OrgMemory is the memory layer for that organization. With WebMCP, the authenticated page registers twenty-one browser-native tools through `document.modelContext` — fourteen read-only, seven that require a human decision. The agent gets schemas and the page's own session. It never sees a credential. |
| **0:35–1:10**<br>**The hero call** | Agent panel. Type the intent. Call fires: `get_orgmemory_briefing({task: "raise worker concurrency on the payments service", service: "payments", surface: "deployment console"})`. Result renders — highlight the `requires_approval` verdict, then each of the 6 memories with its ID. | Here's the tool this product exists for: `get_orgmemory_briefing`. Every other tool answers a question — this one answers an intent. The agent states what it's about to do, and OrgMemory returns a verdict: requires approval. Two prior incidents that started exactly this way. The decision that caps concurrency. The blast radius — payments shares a Postgres cluster with the ledger. And the remembered first-response procedure. Six memories, every line with an ID a person can open. No model in this path: ask twice, get the same verdict twice. |
| **1:10–1:30**<br>Traversal | Activity panel scrolls as `get_orgmemory_incidents`, `get_orgmemory_dependencies`, `get_orgmemory_decisions`, `get_orgmemory_service_context` execute back to back. Zoom on tool name, arguments, result count, latency. | From there the agent follows structure, not screens — incidents, dependencies, decisions, the service profile. Page-defined calls with names, arguments, result counts and latency. Not REST requests relabeled for a demo. No scraping, no tab-switching, no guessing which of six dashboards is current. |
| **1:30–1:55**<br>**The boundary** | `propose_orgmemory_incident` fires. Response reads *proposal created — nothing saved*. The request appears inline in the workspace. A human cursor clicks **Approve**. Audit row appends. | Now the agent learns something new and tries to write it back. It can't. `propose_orgmemory_incident` returns a proposal — nothing is saved. The request appears inline in the workspace, and a person approves it. Agents propose, people decide. That boundary is enforced in the tool, not in a policy doc. |
| **1:55–2:20**<br>Session two | New browser window, fresh session, different agent, empty chat. Same question. The approved incident, procedure, dependency and decision come straight back. | Second session. Different agent, no shared chat, no carried context. It asks the same question — and gets the approved incident, the procedure, the dependency, the decision. This is the part a chat window can't do: the memory outlived the session that produced it, because it lives in the org, not the transcript. |
| **2:20–2:40**<br>Outcome loop | Outcome Loop view: the briefing from 0:35 sits as an **open** ledger row. `record_orgmemory_outcome` fires; row closes with the observed result. | And the loop closes. `record_orgmemory_outcome` writes back what context was served, what action followed, and whether it worked. That briefing is an open ledger row until someone says how it went. That's how the memory gets better instead of just bigger. |
| **2:40–2:52**<br>Close | Back to `/webmcp`. Card with the live URL and the repo link. | Without WebMCP, an agent sees another website. With WebMCP, it inherits the organization's memory — and the organization keeps the decision. It's live at orgmemory dot vercel dot app. |

---

## Voiceover, continuous

Your company already knows why the payments service failed last time. It's in a postmortem nobody reads. So when an AI agent shows up to change that service, it starts from zero — and repeats the outage.

OrgMemory is the memory layer for that organization. With WebMCP, the authenticated page registers twenty-one browser-native tools through document dot model context — fourteen read-only, seven that require a human decision. The agent gets schemas and the page's own session. It never sees a credential.

Here's the tool this product exists for: get OrgMemory briefing. Every other tool answers a question — this one answers an intent. The agent states what it's about to do, and OrgMemory returns a verdict: requires approval. Two prior incidents that started exactly this way. The decision that caps concurrency. The blast radius — payments shares a Postgres cluster with the ledger. And the remembered first-response procedure. Six memories, every line with an I D a person can open. No model in this path: ask twice, get the same verdict twice.

From there the agent follows structure, not screens — incidents, dependencies, decisions, the service profile. Page-defined calls with names, arguments, result counts and latency. Not REST requests relabeled for a demo. No scraping, no tab-switching, no guessing which of six dashboards is current.

Now the agent learns something new and tries to write it back. It can't. Propose OrgMemory incident returns a proposal — nothing is saved. The request appears inline in the workspace, and a person approves it. Agents propose, people decide. That boundary is enforced in the tool, not in a policy doc.

Second session. Different agent, no shared chat, no carried context. It asks the same question — and gets the approved incident, the procedure, the dependency, the decision. This is the part a chat window can't do: the memory outlived the session that produced it, because it lives in the org, not the transcript.

And the loop closes. Record OrgMemory outcome writes back what context was served, what action followed, and whether it worked. That briefing is an open ledger row until someone says how it went. That's how the memory gets better instead of just bigger.

Without WebMCP, an agent sees another website. With WebMCP, it inherits the organization's memory — and the organization keeps the decision. It's live at orgmemory dot vercel dot app.

---

## Production notes

- **Audio is required** by the submission rules. Record VO first, then cut
  picture to it — the timings above assume ~140 wpm; if your read lands faster,
  hold the 0:35–1:10 briefing result longer rather than adding narration.
- **Burn in the tool name** as an on-screen chip the moment each call fires
  (`get_orgmemory_briefing`, `propose_orgmemory_incident`,
  `record_orgmemory_outcome`). Judges scoring *WebMCP Leverage* should never
  have to infer that a call happened.
- **Show `document.modelContext` in the console once, early** (0:15–0:35). It is
  the single strongest proof of a real implementation versus a mocked panel.
- The 1:30–1:55 approval beat is the *Creativity & Ambition* differentiator —
  do not cut it for time. Cut from the traversal beat instead.
- Keep the deployment-console cold open under 15 seconds; it is context, not the
  product.
- Upload public to YouTube, captions on (`captions.srt` can be retimed from this
  cut).
