# Three-minute WebMCP demo storyboard

## One-line story

A browser agent investigates a recurring payments failure through real WebMCP
tools, proposes verified knowledge behind a human approval gate, and hands that
durable context to a completely fresh agent.

## Timed cut

| Time | Screen | Presenter beat |
| --- | --- | --- |
| 00:00–00:14 | Command Center hero | Frame the organizational context problem. |
| 00:14–00:28 | Without / With WebMCP | Contrast UI archaeology with a structured capability. |
| 00:28–00:38 | Authenticated workspace | Establish permission-scoped memory and the 19-tool surface. |
| 00:38–00:52 | Live discovery trace | Prove the browser discovered and invoked a real page tool. |
| 00:52–01:10 | Incidents + service context | Ask why payments is failing again and retrieve precedent. |
| 01:10–01:26 | Dependencies + decisions | Show blast radius and the prior concurrency-cap decision. |
| 01:26–01:44 | Session 1 answer | Turn disconnected records into an actionable first response. |
| 01:44–01:58 | Human approval gate | Show that the agent can propose, but cannot silently write truth. |
| 01:58–02:16 | Fresh-agent bridge | Make the zero-shared-chat handoff explicit. |
| 02:16–02:34 | Session 2 answer | Prove that the new agent starts with retained organizational context. |
| 02:34–02:48 | Governed tool catalog | Separate read capability, proposals, and admin decisions. |
| 02:48–03:00 | Closing hero | Land the product category and value statement. |

## Live presenter runbook

Use this if presenting the product rather than playing the MP4.

1. Open `http://localhost:3000/webmcp` and deliver the opening claim.
2. Open the authenticated workspace. Point out `19 tools`, `13 read-only`, and
   `6 governed`.
3. Ask the WebMCP-capable browser agent to call, in order:

   ```text
   list_orgmemory_spaces()
   get_orgmemory_incidents({service: "payments", project_id: "<WebMCP Demo>"})
   get_orgmemory_service_context({service: "payments", project_id: "<WebMCP Demo>"})
   get_orgmemory_dependencies({service: "payments", project_id: "<WebMCP Demo>"})
   get_orgmemory_decisions({project_id: "<WebMCP Demo>", limit: 5})
   ```

4. Open **WebMCP Activity** and point to the real tool names, arguments, result
   counts, and latency.
5. Return to the Command Center and run **Session 1 — agent investigates**.
6. Pause on **nothing is saved yet**. The presenter, acting as the human
   operator, approves the proposed incident.
7. Run **Session 2 — brand-new agent**. Point to the bridge: no shared chat and
   no carried context.
8. Close on the governed tool filter and the line: “OrgMemory gives WebMCP
   agents organizational memory so they can understand what happened before
   acting on what is happening now.”

## Demo discipline

- Do not call normal REST requests “WebMCP.” Keep the WebMCP Activity panel in
  frame when proving the browser-native boundary.
- Do not imply the agent approved its own proposal. The human demonstrator is
  the decision-maker.
- If the configured model is unavailable, disclose the guided fallback exactly
  as the UI does: tool calls, evidence, and approvals are real; only tool order
  is scripted.
- Never promise a runbook when none is remembered. Missing context is an honest
  signal and should trigger a governed refresh or knowledge proposal.
