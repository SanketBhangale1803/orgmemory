# OrgMemory WebMCP demo — Remotion source

This project renders the three-minute OrgMemory demo as a 1920 × 1080,
30 fps Remotion composition.

## Final challenge submission

`OrgMemoryWebMCPFinal` is the 2:50 challenge cut built around the required route
order: `/` → `/webmcp` → `/approvals` → `/loop` → `/webmcp`. It includes the
final narration, burned-in captions, the named `get_orgmemory_briefing` and
`record_orgmemory_outcome` calls, and a four-second clean end-card hold.

```bash
npx remotion render OrgMemoryWebMCPFinal ../orgmemory-webmcp-final.mp4 \
  --codec=h264 \
  --crf=15 \
  --audio-codec=aac \
  --pixel-format=yuv420p \
  --concurrency=4
```

The YouTube-ready master is `../orgmemory-webmcp-final-submission.mp4`: 170.1
seconds, H.264 High, 1080p30, stereo AAC at 48 kHz, and −16 LUFS integrated.

## Preview

```bash
npm install
npx remotion studio --no-open --port=3100
```

Open `http://localhost:3100/OrgMemoryWebMCP`.

## Render

```bash
npx remotion render OrgMemoryWebMCP ../orgmemory-webmcp-demo-remotion.mp4 \
  --codec=h264 \
  --crf=15 \
  --audio-codec=aac \
  --pixel-format=yuv420p \
  --concurrency=4
```

The main composition is exactly 5,400 frames. The 14 scene durations include
each 18-frame transition overlap, producing an exact 180-second timeline.

## Structure

- `src/scenes/`: one editable component per chapter
- `src/components/ScreenshotScene.tsx`: reusable camera, title, metric, and callout treatment
- `src/components/AnimatedCaptions.tsx`: JSON-backed burned-in captions
- `public/captures/`: product captures, with low-resolution sources sharpened to 1080p
- `public/audio/narration-daniel.mp3`: Daniel (British English) narration
- `public/audio/ambient.wav`: low-level background bed
