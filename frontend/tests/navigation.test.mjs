import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("one registry is the only navigation model", () => {
  const map = readFileSync(new URL("../lib/workspaceMap.ts", import.meta.url), "utf8");
  const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
  // Every destination the product has must be registered, because the command
  // menu and the title bar both read this file and nothing else.
  for (const href of [
    "/workspace",
    "/ask",
    "/work",
    "/loop",
    "/ingest",
    "/connectors",
    "/jobs",
    "/memories",
    "/graph",
    "/profiles",
    "/projects",
    "/updates",
    "/approvals",
    "/conflicts",
    "/drift",
    "/reliability",
    "/audit",
    "/webmcp",
    "/runbooks",
    "/simulation",
    "/integrations",
    "/benchmarks",
    "/settings",
    "/account",
    "/keys",
    "/admin",
  ]) assert.match(map, new RegExp(`href: "${href}"`), `${href} must be registered`);
  // The shell derives titles from the registry rather than keeping its own copy.
  assert.match(shell, /titleFor\(pathname\)/);
  assert.doesNotMatch(shell, /chatSatellites/);
  // The legacy multi-domain header is gone; a second navigation model was the maze.
  assert.doesNotMatch(shell, /from "@\/components\/Nav"/);
});

test("the command menu reaches every registered destination from anywhere", () => {
  const menu = readFileSync(new URL("../components/CommandMenu.tsx", import.meta.url), "utf8");
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  const bar = readFileSync(new URL("../components/ChatBackBar.tsx", import.meta.url), "utf8");
  assert.match(menu, /searchDestinations/);
  assert.match(menu, /event\.metaKey \|\| event\.ctrlKey/);
  assert.match(menu, /key\.toLowerCase\(\) === "k"/);
  // A typed question is answerable from the menu, not just a page name.
  assert.match(menu, /orgmemory\.pending-question/);
  // Both the chat and every satellite page mount it, so the keystroke never dies.
  assert.match(chat, /<CommandMenu/);
  assert.match(bar, /<CommandMenu/);
});

test("pages render real product concepts", () => {
  const pages = [
    ["../app/page.tsx", "Your organization remembers"],
    // The landing page must name the vertical, not the category. "Organizational
    // memory" sells to nobody; engineering organizations are who this is for.
    ["../app/page.tsx", "The memory layer for engineering organizations"],
    ["../app/page.tsx", "WebMCP ready"],
    ["../app/page.tsx", "Incidents, decisions, and owners stay tied to evidence"],
    ["../app/page.tsx", "Agents get briefed before they act"],
    ["../app/page.tsx", "Agents investigate. People authorize"],
    ["../app/page.tsx", "outcome observed"],
    ["../app/loop/page.tsx", "context actually produced correct action"],
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

test("public routes and the isolated WebMCP demo stay separate from the workspace", () => {
  const shell = readFileSync(new URL("../components/AppShell.tsx", import.meta.url), "utf8");
  const map = readFileSync(new URL("../lib/workspaceMap.ts", import.meta.url), "utf8");
  assert.match(shell, /const isLanding = pathname === "\/"/);
  assert.match(shell, /pathname\.startsWith\("\/docs\/"\)/);
  // The challenge build can expose only the isolated WebMCP fixture. The real
  // workspace remains behind the session gate.
  assert.match(shell, /const isPublicWebMCP = isWebMCP && WEBMCP_DEMO_MODE/);
  assert.match(shell, /pathname === "\/login" \|\| isPublicWebMCP/);
  assert.match(shell, /pathname === "\/workspace" \|\| isWebMCP/);
  assert.match(shell, /router\.replace\("\/workspace"\)/);
  assert.match(map, /href: "\/workspace"/);
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
  const bar = readFileSync(new URL("../components/ChatBackBar.tsx", import.meta.url), "utf8");
  assert.match(logo, /runbook-mark/);
  assert.match(logo, />ORGMEMORY</);
  assert.match(bar, /<RunbookMark \/>/);
  assert.doesNotMatch(bar, /className="mark"/);
});

test("browser API calls use the secure session cookie instead of legacy local storage tokens", () => {
  const api = readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8");
  const nextConfig = readFileSync(new URL("../next.config.ts", import.meta.url), "utf8");
  assert.match(api, /credentials: "include"/);
  assert.match(api, /Cannot reach the OrgMemory API/);
  assert.doesNotMatch(api, /localStorage\.getItem\("runbook_token"\)/);
  assert.doesNotMatch(api, /Authorization: `Bearer/);
  assert.match(nextConfig, /type: "host", value: "127\.0\.0\.1"/);
  assert.match(nextConfig, /destination: "http:\/\/localhost:3000\/:path\*"/);
});

test("the hosted demo cannot navigate past authentication before hydration", () => {
  const login = readFileSync(new URL("../app/login/page.tsx", import.meta.url), "utf8");
  const vercel = readFileSync(new URL("../../vercel.json", import.meta.url), "utf8");
  assert.match(login, /WEBMCP_DEMO_MODE \? \(/);
  assert.match(login, /type="button"/);
  assert.match(login, /enterDemo\("google"\)/);
  assert.match(login, /enterDemo\("github"\)/);
  assert.doesNotMatch(login, /WEBMCP_DEMO_MODE \? "\/workspace"/);
  assert.deepEqual(JSON.parse(vercel).rewrites[0], {
    source: "/",
    destination: { service: "frontend" },
  });
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
  assert.match(shell, /const isChat = pathname === "\/workspace" \|\| isWebMCP/);
  // Same model picker and composer the signed-out landing page shows.
  assert.match(chat, /\/api\/models/);
  assert.match(chat, /\/api\/ask/);
  assert.match(chat, /Ask your company memory/);
  assert.match(chat, /Ask OrgMemory anything/);
});

test("the intelligence canvas exposes evidence trails without fabricating retrieval progress", () => {
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  for (const evidenceField of [
    /context_envelope/,
    /retrieval_trace/,
    /memory_units/,
    /related_entities/,
    /likely_cause/,
    /trust_score/,
  ]) assert.match(chat, evidenceField, `chat should preserve ${evidenceField}`);
  assert.match(chat, /Investigation Trail/);
  assert.match(chat, /Observed facts/);
  assert.match(chat, /Permission-trimmed before ranking/);
  assert.match(chat, /Real results will appear as soon as retrieval returns/);
  assert.doesNotMatch(chat, /setInterval\([^)]*retrieval|rotatingStages|fakeProgress/);
  // Answers still distinguish general knowledge and hand code work to an editor.
  assert.match(chat, /general_knowledge/);
  assert.match(chat, /Paste into Cursor, Copilot, or Claude Code/);
});

test("the public Command Orb carries a question into the authenticated workspace", () => {
  const command = readFileSync(new URL("../components/HomeCommandOrb.tsx", import.meta.url), "utf8");
  const chat = readFileSync(new URL("../components/WorkspaceChat.tsx", import.meta.url), "utf8");
  assert.match(command, /orgmemory\.pending-question/);
  assert.match(command, /router\.push\("\/workspace"\)/);
  assert.match(command, /event\.metaKey \|\| event\.ctrlKey/);
  assert.match(chat, /sessionStorage\.getItem\("orgmemory\.pending-question"\)/);
  assert.match(chat, /sessionStorage\.removeItem\("orgmemory\.pending-question"\)/);
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
