import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("navigation keeps domains in the top bar and subdomains in contextual tabs", () => {
  const nav = readFileSync(new URL("../components/Nav.tsx", import.meta.url), "utf8");
  for (const label of [
    "Home",
    "Add knowledge",
    "Memory Graph",
    "Ask OrgMemory",
    "Memory Work",
    "Explore",
    "Memories",
    "Profiles",
    "Change Intelligence",
    "Conflicts",
    "Projects",
    "Ingestion jobs",
    "MCP & integrations",
    "API keys",
    "Settings",
    "Account and workspace",
  ]) assert.match(nav, new RegExp(label));
  assert.doesNotMatch(nav, /sidebar/);
});

test("pages render real product concepts", () => {
  const pages = [
    ["../app/page.tsx", "Your company already knows the answer"],
    ["../app/page.tsx", "Graph foragers"],
    ["../app/page.tsx", "Sources stay cited"],
    ["../app/page.tsx", "Google Workspace"],
    ["../app/page.tsx", "Ask anywhere"],
    ["../app/docs/page.tsx", "Context assembly, typed in Python"],
    ["../app/docs/page.tsx", "Specialists forage"],
    ["../app/login/page.tsx", "Log in to OrgMemory"],
    ["../app/login/page.tsx", "Continue with GitHub"],
    ["../app/login/page.tsx", "Continue with Google"],
    ["../app/login/page.tsx", "Email me a code"],
    ["../app/connectors/page.tsx", "OAuth tokens never reach the browser"],
    ["../app/ingest/page.tsx", "Private repositories supported"],
    ["../app/graph/page.tsx", "Memory Graph"],
    ["../app/graph/page.tsx", "Blast Radius"],
    ["../app/jobs/page.tsx", "graph_nodes_created"],
    ["../app/ask/page.tsx", "trust_score"],
    ["../app/ask/page.tsx", "change_correlation"],
    ["../app/work/page.tsx", "Give OrgMemory an outcome"],
    ["../app/work/page.tsx", "Approve & post"],
    ["../app/work/page.tsx", "Slack message"],
    ["../app/memories/page.tsx", "Atomic facts"],
    ["../app/profiles/page.tsx", "current source-backed memories"],
    ["../app/updates/page.tsx", "What OrgMemory understood"],
    ["../app/conflicts/page.tsx", "source-backed memories disagree"],
    ["../app/benchmarks/page.tsx", "make benchmark"],
    ["../app/keys/page.tsx", "key_prefix"],
    ["../app/admin/page.tsx", "Not connected"],
    ["../app/runbooks/[id]/page.tsx", "Check drift now"],
    ["../app/reliability/page.tsx", "Refresh repository"],
    ["../app/reliability/[id]/page.tsx", "Confirmed source evidence"],
  ];
  for (const [path, phrase] of pages) {
    const source = readFileSync(new URL(path, import.meta.url), "utf8");
    assert.match(source, new RegExp(phrase));
  }
});

test("public landing, docs, login, and authenticated workspace are separate routes", () => {
  const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
  const nav = readFileSync(new URL("../components/Nav.tsx", import.meta.url), "utf8");
  assert.match(shell, /const isLanding = pathname === "\/"/);
  assert.match(shell, /pathname\.startsWith\("\/docs\/"\)/);
  assert.match(shell, /const isPublic = isLanding \|\| isDocs \|\| pathname === "\/login"/);
  assert.match(shell, /router\.replace\("\/workspace"\)/);
  assert.match(nav, /href: "\/workspace"/);
});

test("authenticated entry opens quickly while still showing a securing state", () => {
  const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
  assert.match(shell, /SECURING_MIN_MS = 450/);
  assert.match(shell, /SECURING_MIN_MS - \(Date\.now\(\) - securingStartedAt\)/);
  assert.match(shell, /Loading authorized company context/);
  assert.match(shell, /window\.clearTimeout\(securingTimer\)/);
});

test("the OrgMemory vector identity replaces the placeholder mark", () => {
  const logo = readFileSync(new URL("../components/RunbookLogo.tsx", import.meta.url), "utf8");
  const nav = readFileSync(new URL("../components/Nav.tsx", import.meta.url), "utf8");
  assert.match(logo, /runbook-mark/);
  assert.match(logo, />ORGMEMORY</);
  assert.match(nav, /<RunbookLogo inverted/);
  assert.doesNotMatch(nav, /className="mark"/);
});

test("browser API calls use the secure session cookie instead of legacy local storage tokens", () => {
  const api = readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8");
  const middleware = readFileSync(new URL("../middleware.ts", import.meta.url), "utf8");
  assert.match(api, /credentials: "include"/);
  assert.match(api, /Cannot reach the OrgMemory API/);
  assert.doesNotMatch(api, /localStorage\.getItem\("runbook_token"\)/);
  assert.doesNotMatch(api, /Authorization: `Bearer/);
  assert.match(middleware, /request\.headers\.get\("host"\)/);
  assert.match(middleware, /requestHost !== "127\.0\.0\.1"/);
  assert.match(middleware, /canonicalUrl\.hostname = "localhost"/);
});

test("no page fabricates metrics: benchmark page requires a real report", () => {
  const source = readFileSync(new URL("../app/benchmarks/page.tsx", import.meta.url), "utf8");
  assert.match(source, /No benchmark report has been generated yet/);
  assert.doesNotMatch(source, /\b0\.9[0-9]\b/, "no hardcoded metric values");
});

test("the post-login surface is a chat, not a dashboard", () => {
  const workspace = readFileSync(new URL("../app/workspace/page.tsx", import.meta.url), "utf8");
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
  assert.match(workspace, /<WorkspaceChat/);
  assert.match(shell, /const isChat = pathname === "\/workspace"/);
  // Same model picker and composer the signed-out landing page shows.
  assert.match(chat, /\/api\/models/);
  assert.match(chat, /\/api\/ask/);
  assert.match(chat, /What do you need to know\?/);
});

test("the chat hides retrieval mechanics from the answer surface", () => {
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  for (const mechanic of [
    /context_envelope/,
    /token_budget/,
    /retrieval_trace/,
    /chunk_id.*confidence/,
    /activation_swarm/,
    /trust_score/,
  ]) assert.doesNotMatch(chat, mechanic, `chat must not surface ${mechanic}`);
  // Answers still say where they came from, and hand code work to an editor.
  assert.match(chat, /general_knowledge/);
  assert.match(chat, /Paste into Cursor, Copilot, or Claude Code/);
});

test("Ask renders answer markdown as typography instead of raw asterisks", () => {
  const ask = readFileSync(new URL("../app/ask/page.tsx", import.meta.url), "utf8");
  const markdown = readFileSync(new URL("../components/MarkdownAnswer.tsx", import.meta.url), "utf8");
  assert.match(ask, /<MarkdownAnswer>{result\.answer}<\/MarkdownAnswer>/);
  assert.match(markdown, /<strong key=/);
  assert.match(markdown, /<em key=/);
  assert.match(markdown, /<code key=/);
  assert.doesNotMatch(ask, /<p>{result\.answer}<\/p>/);
});

test("the chat closes the outcome loop it opened", () => {
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  // Asking records which surface asked, so the corpus can tell a person in the
  // web chat apart from an agent calling through MCP.
  assert.match(chat, /surface: "web"/);
  // Copying a handoff is the implicit signal; the rating is the explicit one.
  assert.match(chat, /noteAction\(contextEventId, "handoff_copied"/);
  assert.match(chat, /\/api\/outcomes\/actions/);
  assert.match(chat, /\/api\/outcomes\/outcomes/);
  assert.match(chat, /Did this work\?/);
  // Recording must never surface as an error to the person who just asked.
  assert.match(chat, /catch\(\(\) => undefined\)/);
});
