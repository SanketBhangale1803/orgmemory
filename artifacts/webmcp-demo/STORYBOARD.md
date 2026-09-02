# OrgMemory WebMCP — three-minute demo

The first 94 seconds demonstrate the browser-native WebMCP path. The remaining
86 seconds show how the rest of OrgMemory creates, governs, activates, and
measures the memory returned to browser agents.

## Timed cut

| Time | Screen | Functional beat |
| --- | --- | --- |
| 00:00–00:12 | WebMCP Command Center | Establish the current 21-tool browser surface. |
| 00:12–00:22 | Authenticated workspace | Show page registration and the signed-in access boundary. |
| 00:22–00:36 | WebMCP Activity | Show real tool discovery and the first browser call. |
| 00:36–00:54 | WebMCP Activity | Inspect the task briefing, memories, verdict, arguments, counts, and latency. |
| 00:54–01:08 | Session 1 | Use incident, dependency, and decision memory to explain the failure mode. |
| 01:08–01:20 | Human approval gate | Demonstrate that write-capable tools create proposals, not truth. |
| 01:20–01:34 | Session 2 | Retrieve the approved memory in a fresh agent with no shared chat. |
| 01:34–01:46 | Add Knowledge | Show the supported source-ingest paths. |
| 01:46–01:58 | Memories | Show typed, scoped, atomic records. |
| 01:58–02:10 | Profiles | Show a current payments profile assembled at request time. |
| 02:10–02:22 | Memory Graph | Show provenance and relationship traversal. |
| 02:22–02:34 | Memory Work | Activate evidence and prepare a governed output. |
| 02:34–02:50 | Outcome Loop | Track served context, action, and observed result. |
| 02:50–03:00 | WebMCP Command Center | Summarize the complete application loop. |

## WebMCP calls shown

```text
list_orgmemory_spaces()
get_orgmemory_briefing({
  task: "raise worker concurrency on the payments service",
  service: "payments",
  project_id: "<WebMCP Demo>",
  surface: "deployment console"
})
get_orgmemory_incidents({service: "payments", project_id: "<WebMCP Demo>"})
get_orgmemory_dependencies({service: "payments", project_id: "<WebMCP Demo>"})
get_orgmemory_decisions({project_id: "<WebMCP Demo>", limit: 5})
```

The recorded briefing returned six memories and a `requires_approval` verdict.
The activity panel shows the page-defined tool names, arguments, result counts,
and latency. The call also created the open context row shown later in the
Outcome Loop.

## Rendering

- 1920 × 1080 at 30 fps
- Remotion 4 composition with one editable component per chapter
- Frame-driven camera movement, metric cards, and evidence callouts
- 18-frame fades and directional slides using `TransitionSeries`
- Sharpened 1080p source captures and a bundled SF sans-serif font
- Daniel (British English) narration with a low-level ambient bed
- JSON-backed burned-in captions plus an embedded English subtitle track
- Exact duration: 180 seconds
