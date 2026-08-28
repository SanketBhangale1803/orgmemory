# OrgMemory WebMCP demo

This folder contains a self-contained, exactly three-minute product demo for
OrgMemory's WebMCP story.

## Core claim

> Without WebMCP, an agent sees another website. With WebMCP, the agent gains
> the organization's memory.

The demo proves four things:

1. The authenticated workspace exposes a real page-native tool surface through
   `document.modelContext.registerTool()`.
2. A browser agent can retrieve incidents, service context, dependencies, and
   decisions without scraping the UI.
3. Agent writes are proposals. A person remains the approval boundary.
4. A brand-new agent with no shared chat starts ahead because verified context
   survives in OrgMemory.

## Deliverables

- `orgmemory-webmcp-demo.mp4` — final 03:00 narrated demo
- `orgmemory-webmcp-demo-poster.png` — preview frame
- `STORYBOARD.md` — timed presenter and editing runbook
- `narration.txt` — full voiceover
- `captions.srt` — timed English captions
- `captures/` — frames captured from the running product
- `render-demo.sh` — reproducible renderer

## Re-render

The renderer requires macOS `say` and `ffmpeg`:

```bash
bash artifacts/webmcp-demo/render-demo.sh
```

The resulting video is normalized to 1920×1080, 30 fps, exactly 180 seconds,
with a narration/music mix and an embedded English subtitle track.
