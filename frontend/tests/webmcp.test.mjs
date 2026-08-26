import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const webmcp = readFileSync(new URL("../lib/webmcp.ts", import.meta.url), "utf8");
const hook = readFileSync(
  new URL("../hooks/useOrgMemoryWebMCP.ts", import.meta.url),
  "utf8",
);
const chat = readFileSync(
  new URL("../components/WorkspaceChat.tsx", import.meta.url),
  "utf8",
);
const types = readFileSync(new URL("../types/webmcp.d.ts", import.meta.url), "utf8");

const compiled = ts.transpileModule(webmcp, {
  compilerOptions: {
    module: ts.ModuleKind.ESNext,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;
const runtime = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);

test("the authenticated workspace registers four browser-native WebMCP tools", () => {
  assert.match(types, /interface Document/);
  assert.match(types, /modelContext\?: WebMCPModelContext/);
  assert.match(webmcp, /document\.modelContext\.registerTool|modelContext\.registerTool/);

  for (const tool of [
    "list_orgmemory_spaces",
    "ask_orgmemory",
    "inspect_orgmemory_changes",
    "propose_repository_refresh",
  ]) {
    assert.match(webmcp, new RegExp(`name: "${tool}"`));
  }

  assert.match(webmcp, /readOnlyHint: true/);
  assert.match(webmcp, /destructiveHint: false/);
  assert.match(webmcp, /openWorldHint: false/);
  assert.match(webmcp, /additionalProperties: false/g);
});

test("WebMCP registration is feature-detected and cleaned up with page lifecycle", () => {
  assert.match(webmcp, /!document\.modelContext/);
  assert.match(webmcp, /new AbortController\(\)/);
  assert.match(webmcp, /signal: controller\.signal/);
  assert.match(webmcp, /dispose: \(\) => controller\.abort\(\)/);
  assert.match(hook, /registration\.dispose\(\)/);
  assert.match(hook, /setStatus\(registration\.supported \? "ready" : "unsupported"\)/);
});

test("browser-agent questions reuse the secure API and update the visible conversation", () => {
  assert.match(chat, /surface: "web" \| "webmcp"/);
  assert.match(chat, /ask\(question, projectId, "webmcp", requestedScope\)/);
  assert.match(chat, /setTurns\(\(current\) => \[\.\.\.current, \{ question \}\]\)/);
  assert.match(webmcp, /source citations/);
  assert.match(webmcp, /options\.ask\(question, project\.id, scope\)/);
  assert.match(chat, /data-webmcp-status=\{webMCP\.status\}/);
  assert.match(chat, /Four browser-native WebMCP tools are available/);
});

test("WebMCP validates project access before calling scoped backend endpoints", () => {
  assert.match(webmcp, /spaces\.find\(\(space\) => space\.id === requested\)/);
  assert.match(webmcp, /Choose a project_id returned by list_orgmemory_spaces/);
  assert.match(chat, /encodeURIComponent\(projectId\)/);
  assert.match(chat, /credentials: "include"|from "@\/lib\/api"/);
});

test("the real WebMCP implementation registers, invokes, and unregisters all tools", async () => {
  const registered = new Map();
  const previousDocument = globalThis.document;
  globalThis.document = {
    modelContext: {
      async registerTool(tool, { signal }) {
        registered.set(tool.name, tool);
        signal.addEventListener("abort", () => registered.delete(tool.name), { once: true });
      },
    },
  };

  const calls = [];
  try {
    const registration = await runtime.registerOrgMemoryWebMCP({
      spaces: [{ id: "prj_demo", name: "Demo", repository: "acme/demo" }],
      getActiveProjectId: () => "prj_demo",
      async ask(question, projectId, scope) {
        calls.push({ kind: "ask", question, projectId, scope });
        return {
          answer: "Checkout is owned by Platform.",
          answer_sufficient: true,
          answer_scope: "company_memory",
          resolved_subject: "checkout",
          searched_sources: 2,
          evidence: [
            {
              source_title: "Service owners",
              source_type: "document",
              source_url: "https://example.test/owners",
            },
          ],
        };
      },
      async inspectChanges(projectId, limit) {
        calls.push({ kind: "changes", projectId, limit });
        return [
          {
            id: "chg_1",
            source_id: "src_1",
            created_at: "2026-08-25T12:00:00Z",
            review_status: "needs_review",
            added: ["mem_1"],
            conflicts: ["mem_2"],
          },
        ];
      },
      async proposeRepositoryRefresh(projectId, reason) {
        calls.push({ kind: "refresh", projectId, reason });
        return {
          id: "refresh_1",
          project_id: projectId,
          repository: "https://github.com/acme/demo.git",
          reason,
          status: "pending_approval",
          requested_at: "2026-08-26T12:00:00Z",
        };
      },
    });

    assert.equal(registration.supported, true);
    assert.equal(registration.toolCount, 4);
    assert.deepEqual([...registered.keys()], [
      "list_orgmemory_spaces",
      "ask_orgmemory",
      "inspect_orgmemory_changes",
      "propose_repository_refresh",
    ]);

    const spaces = await registered.get("list_orgmemory_spaces").execute({});
    assert.equal(spaces.structuredContent.spaces[0].project_id, "prj_demo");

    const answer = await registered.get("ask_orgmemory").execute({
      question: "Who owns checkout?",
      project_id: "prj_demo",
      scope: "project",
    });
    assert.equal(answer.structuredContent.answer_sufficient, true);
    assert.equal(answer.structuredContent.evidence[0].title, "Service owners");

    const changes = await registered.get("inspect_orgmemory_changes").execute({
      project_id: "prj_demo",
      limit: 500,
    });
    assert.equal(changes.structuredContent.changes[0].conflicts, 1);
    const refresh = await registered.get("propose_repository_refresh").execute({
      project_id: "prj_demo",
      reason: "The latest commit evidence is stale.",
    });
    assert.equal(refresh.structuredContent.status, "pending_approval");
    assert.deepEqual(calls, [
      {
        kind: "ask",
        question: "Who owns checkout?",
        projectId: "prj_demo",
        scope: "project",
      },
      { kind: "changes", projectId: "prj_demo", limit: 50 },
      {
        kind: "refresh",
        projectId: "prj_demo",
        reason: "The latest commit evidence is stale.",
      },
    ]);

    await assert.rejects(
      registered.get("ask_orgmemory").execute({
        question: "Who owns checkout?",
        project_id: "prj_not_authorized",
      }),
      /Choose a project_id returned by list_orgmemory_spaces/,
    );

    registration.dispose();
    assert.equal(registered.size, 0);
  } finally {
    if (previousDocument === undefined) delete globalThis.document;
    else globalThis.document = previousDocument;
  }
});
