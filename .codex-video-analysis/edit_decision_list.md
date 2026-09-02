# OrgMemory / WebMCP Hackathon Demo — Edit Decision List

Prepared: 2026-08-30  
Target output: `/Users/sanket/Desktop/webmcp/orgmemory_demo_final.mp4`

## Editorial finding

Only script beats 1–4 have usable narration in the supplied recordings. The intended payments briefing was recorded, but the on-screen run does **not** produce the scripted result: it calls generic search tools, returns `0 matching memories`, never shows a `payments` scope selection, and never reaches `get_orgmemory_briefing`. The remaining recordings are silent screen captures or contain unrelated product states. Per the instruction not to fabricate missing footage, the render is therefore a polished **partial cut** covering beats 1–4 only; beats 5–14 are explicitly logged as gaps below.

## Source inventory

All eight sources are 3020×1550 HEVC with a 120 fps container rate/timebase and 48 kHz stereo AAC. Their actual variable capture rates differ (approximately 20–54 fps), so the master is normalized to a true 30 fps rather than duplicating frames to 120 fps.

| Source | Duration | Use decision |
|---|---:|---|
| `loading part.mov` | 00:23.041 | Exclude: unrelated “why are the payments failing” query, prolonged loading, Finder overlay near 00:20. |
| `Screen Recording 2026-08-30 at 8.18.26 PM.mov` | 03:51.057 | Exclude from final: silent/repetitive OAuth demo, browser autocomplete overlay near 03:02, unrelated external credits page near 03:26. |
| `webmcp loading.mov` | 00:59.823 | Exclude: editor/script is visible around 00:14–00:25; the subsequent payments run returns zero matches and never reaches the scripted briefing. |
| `part-1.mov` | 00:28.860 | Use: only clean narrated source for beats 1–2; clean home-page visuals and no auth/error state. |
| `part-2.mov` | 00:47.325 | Audio only, 00:00–00:24.650: only narrated source for beats 3–4. Its login/OAuth/loading visuals are replaced by a clean authenticated WebMCP view. |
| `Screen Recording 2026-08-30 at 8.22.55 PM.mov` | 00:07.934 | Exclude: “Are we ready for launch now?” duplicate; not the required “tomorrow” follow-up. |
| `Screen Recording 2026-08-30 at 8.23.38 PM.mov` | 00:36.995 | Use video only, 00:00–00:24.650: clean authenticated WebMCP page and the resolved “Are we ready to launch tomorrow?” response. Stop well before the context-menu overlay near 00:34. |
| `webmcp-main.mov` | 00:51.960 | Exclude entirely: payments searches return zero matches; visible `Authentication required` at about 00:07–00:29 and `No access to space …` at about 00:46–end. |

## Final cut sequence

Hard cuts are used consistently. Both segments retain the 3020×1550 canvas and are normalized to 30 fps for a stable, broadly compatible master. Narration is cleaned with a high-pass filter and loudness normalization; no synthetic speech or invented product result is added.

| Cut | Output range | Video source and in/out | Audio source and in/out | Script coverage | Why this selection |
|---:|---:|---|---|---|---|
| 1 | 00:00.000–00:28.200 | `part-1.mov` 00:00.000–00:28.200 | `part-1.mov` 00:00.000–00:28.200 | Beats 1–2 | Sole complete, intelligible narration for the setup; clean home-page movement with a natural visual reset between the two beats. |
| 2 | 00:28.200–00:52.850 | `Screen Recording 2026-08-30 at 8.23.38 PM.mov` 00:00.000–00:24.650 | `part-2.mov` 00:00.000–00:24.650 | Beats 3–4 | Replaces the source's login/OAuth sequence with a clean authenticated WebMCP view. Also uses the only permitted resolved launch take: “Are we ready to launch tomorrow?” → `READY — 0 blockers, 5 checklist items.` |

Expected runtime: approximately **00:52.850**. This is below 60 seconds because the supplied footage does not contain a clean scripted briefing or narration for beats 5–14; no padding is added.

## Beat-by-beat audit

| Beat | Source / timestamps | Decision and justification |
|---:|---|---|
| 1 | `part-1.mov` 00:00.000–00:11.950 | **Use.** Clean opening explanation on the home page. This sole take says “incidents, decisions, and dependencies”; no alternate with the exact added “runbooks” wording exists. |
| 2 | `part-1.mov` 00:12.300–00:28.200 | **Use.** Clean continuation; semantically matches the target, though the sole take says “other docs” rather than “postmortems.” |
| 3 | Audio: `part-2.mov` 00:00.000–00:15.700; video: resolved authenticated take 00:00.000–00:15.700 | **Use.** The narration is intelligible; authenticated WebMCP visuals replace the mismatched login flow. |
| 4 | Audio: `part-2.mov` 00:15.700–00:24.650; video: resolved authenticated take 00:15.700–00:24.650 | **Use.** Sole narrated take; clean WebMCP/permission context, without showing an auth failure. |
| 5 — demo action | `webmcp loading.mov` 00:26.000–00:59.823 examined | **Gap / exclude.** It types “Restart the payments connection pool” but never shows the required `payments` selection. Submitting it starts a wrong generic-search path that returns zero matches. |
| 6 | `webmcp loading.mov` and `webmcp-main.mov` examined | **Gap / exclude.** No clean footage calls `get_orgmemory_briefing`; the visible runs call `search_orgmemory_records` instead. |
| 7 | Same sources | **Gap / exclude.** No product footage returns `requires approval`, the two incidents, concurrency decision, Postgres/ledger blast radius, or first-response procedure. Those words appear only in an editor containing the production script, which is not usable demo footage. |
| 8 | Same sources | **Gap / exclude.** No clean payments briefing with verifiable memory IDs exists. OAuth-related memory IDs are unrelated to the target beat. |
| 9 | `Screen Recording 2026-08-30 at 8.23.38 PM.mov` 00:00.000–00:08.000 reviewed | **Narration gap.** The clean deterministic readiness response is used earlier as authenticated B-roll under beats 3–4, but there is no script-ordered narration for this beat. |
| 10 | All sources examined | **Gap.** No clean footage contrasts a read-only payments investigation with a disruptive payments action using the intended-action boundary. |
| 11 | Long recording around 03:04–03:07 reviewed | **Gap / exclude.** An approvals page exists only briefly, is unrelated to the payments briefing, and has no matching narration; inserting it would imply a result the recorded demo did not produce. |
| 12 | Long recording around 02:34–02:44 reviewed | **Gap / exclude.** Outcome-loop page exists as silent unrelated B-roll, but there is no `record_orgmemory_outcome` action tied to the payments briefing and no narration. |
| 13 | `part-1.mov` home page available | **Narration gap.** Home footage exists, but the closing narration was not recorded; footage is not repeated as silent padding. |
| 14 | `part-1.mov` home page available | **Narration gap.** No recorded “OrgMemory: put what your organization has learned to work” close. |

## “Can we launch” take comparison

1. `Screen Recording 2026-08-30 at 8.18.26 PM.mov` — repeated “Now are we ready for launch?” material embedded in a long, silent, repetitive OAuth sequence. **Excluded** as the repeated/dead-end take.
2. `Screen Recording 2026-08-30 at 8.22.55 PM.mov` — “Are we ready for launch now?” **Excluded** because it is not the specified “tomorrow” follow-up.
3. `Screen Recording 2026-08-30 at 8.23.38 PM.mov` — “Are we ready to launch tomorrow?” with a resolved `READY — 0 blockers, 5 checklist items` answer. **Used** as the clean authenticated WebMCP visual under beats 3–4.

## Critical exclusion audit

- `webmcp-main.mov` is excluded in full because it visibly contains `Authentication required` and `No access to space …` states.
- The login/OAuth/loading visuals in `part-2.mov` are not used; only its narration is retained.
- `webmcp loading.mov` 00:14–00:25 is excluded because the editor and the written production script are visibly on screen.
- `webmcp loading.mov` 00:26–end is excluded because the demo takes the wrong tool path and returns zero matches.
- `loading part.mov` is excluded because the query is unrelated, it sits in a loading state, and a Finder overlay appears near 00:20.
- The long recording's browser autocomplete overlay and unrelated external credits page are excluded.
- No synthetic narration, reconstructed product output, or script-as-product footage is used.

## Render specification

- Container: MP4
- Video: H.264, 3020×1550, 30 fps, yuv420p
- Audio: AAC, 48 kHz stereo
- Edit style: hard cut
- Fast-start metadata enabled
