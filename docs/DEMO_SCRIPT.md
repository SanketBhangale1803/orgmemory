# OrgMemory — 3-minute demo script

For the OpenAI WebMCP Challenge submission. Judged on WebMCP Leverage, Execution,
Potential Impact, and Creativity & Ambition — equally weighted. Every beat below
is chosen to land one of those four, and the timings assume a normal speaking
pace (~150 wpm), so the narration text is already cut to fit.

## Before you hit record

```bash
# 1. Backend
cd backend && .venv/bin/python -m uvicorn app.main:app --port 8000

# 2. Frontend — never run `npm run build` while this is up, it clobbers .next
cd frontend && npm run dev

# 3. Clear the three junk proposals left over from an old agent run.
#    One has parser scaffolding in its title and it is on camera in beat 4.
backend/.venv/bin/python -c "
import sqlite3; c=sqlite3.connect('data/runbook.db')
c.execute(\"update memory_proposals set status='denied' where status='pending_approval' and subject like '%TOOL CALL%'\"); c.commit()"
```

Sign in at `/login` (dev login is fine), then pre-warm every page you will show
— `/`, `/workspace`, `/webmcp`, `/loop` — so nothing compiles on camera. Set the
browser to 1440×900 and hide bookmarks. Record with QuickTime (File → New Screen
Recording) or Screen Studio if you want automatic zooms.

---

## 0:00–0:22 · The problem (landing page)

**Screen:** `/` — hold on the hero, then scroll slowly through the four cards.

> "Every engineering org already knows why its payments service failed last time.
> That knowledge is in a postmortem nobody reads, a Slack thread nobody can find,
> and one engineer's head. So when an AI agent shows up to change something, it
> starts from zero — and repeats the outage you already had.
>
> OrgMemory is the memory layer for engineering organizations. And through
> WebMCP, it hands that memory to the agent *before* it acts."

**Land:** the eyebrow — "the memory layer for engineering organizations" — and
the live counter: 21 tools, 14 read-only, 6 human-governed.

---

## 0:22–0:45 · One keystroke (command menu)

**Screen:** `/workspace`, press ⌘K, scroll the groups, type `approv`.

> "The workspace is a chat, not a dashboard. And there's one thing to learn:
> Command-K. Twenty-six places, one keystroke — every one of them reachable,
> and the approvals queue showing three decisions waiting on a person.
> Type a question instead of a page name and it answers from company memory."

**Land:** the footer — "26 places · one keystroke." This is your Execution point:
it reads as a finished product, not a hackathon surface.

---

## 0:45–1:45 · The briefing (**the centerpiece — give it the most time**)

**Screen:** `/webmcp`, scroll to "Ask before you act, from anywhere on the web."
Type `restart the payments connection pool`, service `payments`, hit **Brief me**.

> "Here's the tool the product exists for. Every other WebMCP tool answers a
> question. This one answers an *intent* — I'm about to do this thing.
>
> Watch. The agent says what it's about to do, and OrgMemory comes back with:
> requires approval. Two prior incidents that started exactly this way. The
> decision to cap worker concurrency that constrains it. The blast radius — this
> service shares a Postgres cluster with the ledger. And the remembered
> first-response procedure.
>
> Every line carries a memory ID you can open. And no model runs in this path —
> ask twice, get the same verdict twice. An agent about to restart production
> needs a control, not a summary."

Then click the second example, **raise worker concurrency on payments**:

> "Different intent, same discipline. And a read-only intent comes back
> 'proceed' — the boundary is real, not decorative."

**Land:** the amber `REQUIRES APPROVAL` chip and the `mem_...` IDs. This is your
WebMCP Leverage *and* Creativity point in one shot.

---

## 1:45–2:15 · The boundary (approvals)

**Screen:** the `requires_approval` block, then ⌘K → Approvals.

> "OrgMemory will not approve it for you. Three permission tiers, and an agent
> can tell them apart from the annotations alone. Reads are permission-trimmed on
> the server. An outcome report appends to a ledger and changes no knowledge.
> And the only path for a single fact into company memory is a proposal a person
> approves. Capability is never authorization."

---

## 2:15–2:50 · The loop (why this compounds)

**Screen:** `/loop`. Hold on the metric row, then one closed ledger entry.

> "And this is the part a better model can't copy. Serving that briefing opened a
> row here. The agent closes it with `record_orgmemory_outcome` — what it did,
> and whether it worked.
>
> Context served, action taken, outcome observed. Forty-six contexts served so
> far. This one is closed: the agent followed the remembered procedure, and the
> pool recovered without a restart.
>
> Anyone can ingest the same Slack and the same repos. Only this workspace
> accumulates the record of which context actually produced correct action here."

**Land:** the green-edged closed entry with `served → action → outcome`. This is
your Potential Impact point.

---

## 2:50–3:00 · Close

**Screen:** back to `/webmcp`, tool manifest visible.

> "Twenty-one browser-native tools. An agent that gets briefed before it acts,
> and reports back after. OrgMemory — your organization remembers."

---

## If you have to cut

Cut in this order: the second briefing example (0:15), the approvals page visit
(0:15), the landing-page scroll (0:10). **Never cut the briefing beat or the
loop** — those two are the entire differentiated claim, and everything else is
context for them.

## Recording notes

- Type the briefing task by hand on camera. Watching it get typed sells that it
  is a live call; a pre-filled field reads as a mock.
- Pause ~1.5s on the verdict chip before narrating it. It is the single most
  important frame in the video.
- Don't show the `/webmcp` "Session 1 — agent investigates" console unless you
  have a model key configured and have rehearsed it; it depends on a live LLM
  and can rate-limit mid-take.
- Keep the browser DevTools closed — the Next.js dev overlay badge appears in
  the bottom-left corner otherwise.
