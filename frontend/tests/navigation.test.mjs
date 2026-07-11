import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
test("navigation exposes all enterprise product sections", () => {
  const nav = readFileSync(new URL("../components/Nav.tsx", import.meta.url), "utf8");
  for (const label of [
    "Login",
    "Overview",
    "Connectors",
    "Projects",
    "Repo Graph",
    "Ask Runbook",
    "Runbooks",
    "Ingestion Jobs",
    "Runbook Drift",
    "Runbook Reliability",
    "Simulation",
    "Approvals",
    "Audit log",
    "Admin & security",
    "MCP & integrations",
    "API keys",
    "Benchmark Reports",
    "Settings",
  ]) assert.match(nav, new RegExp(label));
});

test("pages render real product concepts", () => {
  const pages = [
    ["../app/login/page.tsx", "Runbook Login"],
    ["../app/graph/page.tsx", "Evidence Paths"],
    ["../app/graph/page.tsx", "Blast Radius"],
    ["../app/jobs/page.tsx", "graph_nodes_created"],
    ["../app/ask/page.tsx", "trust_score"],
    ["../app/ask/page.tsx", "change_correlation"],
    ["../app/drift/page.tsx", "drift_status"],
    ["../app/simulation/page.tsx", "applicable_runbook"],
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

test("no page fabricates metrics: benchmark page requires a real report", () => {
  const source = readFileSync(new URL("../app/benchmarks/page.tsx", import.meta.url), "utf8");
  assert.match(source, /No benchmark report has been generated yet/);
  assert.doesNotMatch(source, /\b0\.9[0-9]\b/, "no hardcoded metric values");
});
