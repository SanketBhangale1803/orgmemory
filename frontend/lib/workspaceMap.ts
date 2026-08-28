/* One registry of every place in the product.
 *
 * The maze was never the number of pages — it was that each surface kept its own
 * private list of them. The header knew six domains, the shell knew twenty-three
 * titles, and nothing knew all of it, so pages existed that could only be reached
 * by typing a URL. Everything that navigates now reads this file: the command
 * menu, the satellite title bar, and the map page. Adding a route here makes it
 * reachable everywhere at once, and forgetting to add one is visible immediately
 * because the page loses its title.
 */

export type DestinationGroup = "Ask" | "Knowledge" | "Govern" | "Agents" | "Admin";

export type Destination = {
  href: string;
  /* What the title bar shows on the page itself. */
  title: string;
  /* What it does, in the command menu. Written for someone who has not seen the
     page yet, which rules out restating the title with different words. */
  summary: string;
  group: DestinationGroup;
  /* Extra search terms — what someone would type when they do not know the name
     we chose. "logs" finds the audit trail; "repo" finds memory spaces. */
  keywords?: string[];
  /* Owners and admins only. Server-side authorization is still the boundary;
     this only stops us advertising a door that will not open. */
  adminOnly?: boolean;
  /* Shown in the top bar. Everything else lives one keystroke away in ⌘K. */
  primary?: boolean;
};

export const DESTINATIONS: Destination[] = [
  {
    href: "/workspace",
    title: "Chat",
    summary: "Ask your company anything and get an answer with its evidence.",
    group: "Ask",
    keywords: ["home", "ask", "question", "chat", "search"],
    primary: true,
  },
  {
    href: "/ask",
    title: "Ask OrgMemory",
    summary: "The single-question view, with the full retrieval trace expanded.",
    group: "Ask",
    keywords: ["query", "retrieval", "trace"],
  },
  {
    href: "/work",
    title: "Memory work",
    summary: "Turn an outcome you describe into a source-backed work package for an AI worker.",
    group: "Ask",
    keywords: ["handoff", "packet", "agent", "task", "brief"],
  },
  {
    href: "/loop",
    title: "Outcome loop",
    summary:
      "Context served, action taken, outcome observed — the record of which context actually produced correct action here.",
    group: "Ask",
    keywords: ["outcomes", "ledger", "feedback", "training", "acceptance", "skills", "precedent"],
    primary: true,
  },

  {
    href: "/ingest",
    title: "Add knowledge",
    summary: "Bring in a repository, a document, or a transcript.",
    group: "Knowledge",
    keywords: ["upload", "import", "github", "repository", "file", "new"],
    primary: true,
  },
  {
    href: "/connectors",
    title: "Connections",
    summary: "Connect GitHub, Slack, Drive, and the rest of the systems the team already uses.",
    group: "Knowledge",
    keywords: ["integrations", "github", "slack", "oauth", "sources"],
  },
  {
    href: "/jobs",
    title: "Ingestion jobs",
    summary: "Watch what is currently being read into memory, and what failed.",
    group: "Knowledge",
    keywords: ["status", "queue", "sync", "progress"],
  },
  {
    href: "/memories",
    title: "Memories",
    summary: "Every atomic fact, decision, policy, owner, and dependency, with its sources.",
    group: "Knowledge",
    keywords: ["facts", "units", "browse", "knowledge"],
  },
  {
    href: "/graph",
    title: "Memory graph",
    summary: "How services, people, repositories, and decisions actually connect.",
    group: "Knowledge",
    keywords: ["entities", "relationships", "map", "visual", "blast radius"],
  },
  {
    href: "/profiles",
    title: "Profiles",
    summary: "Assembled current truth for the company, a project, a repository, or a service.",
    group: "Knowledge",
    keywords: ["company", "service", "summary", "current"],
  },
  {
    href: "/projects",
    title: "Memory spaces",
    summary: "The projects memory is partitioned into, and what each one holds.",
    group: "Knowledge",
    keywords: ["repos", "repositories", "spaces", "workspaces"],
  },
  {
    href: "/updates",
    title: "Change intelligence",
    summary: "What changed in the sources, and which memories and artifacts it affected.",
    group: "Knowledge",
    keywords: ["diff", "changes", "revisions", "impact"],
  },

  {
    href: "/approvals",
    title: "Approvals",
    summary: "Every decision waiting on a person — agent proposals and refresh requests.",
    group: "Govern",
    keywords: ["inbox", "pending", "approve", "deny", "proposals", "review"],
    primary: true,
  },
  {
    href: "/conflicts",
    title: "Conflicts",
    summary: "Where source-backed memories disagree with each other.",
    group: "Govern",
    keywords: ["contradictions", "disagree", "stale"],
  },
  {
    href: "/drift",
    title: "Drift checks",
    summary: "Memories the sources no longer support, and what needs re-verifying.",
    group: "Govern",
    keywords: ["stale", "freshness", "verify", "rot"],
  },
  {
    href: "/reliability",
    title: "Reliability",
    summary: "Assertions under review and the change impacts behind them.",
    group: "Govern",
    keywords: ["assertions", "impact", "risk", "confidence"],
  },
  {
    href: "/audit",
    title: "Audit log",
    summary: "The immutable record of everything read, written, approved, and denied.",
    group: "Govern",
    keywords: ["history", "log", "events", "compliance", "trail"],
  },

  {
    href: "/webmcp",
    title: "WebMCP",
    summary:
      "The browser-native tool surface this page exposes to AI agents, with the live call trace.",
    group: "Agents",
    keywords: ["agents", "tools", "mcp", "browser", "command center", "trace"],
    primary: true,
  },
  {
    href: "/runbooks",
    title: "Runbooks",
    summary: "Procedures extracted from cited operational evidence.",
    group: "Agents",
    keywords: ["procedures", "steps", "playbook", "incident"],
  },
  {
    href: "/simulation",
    title: "Simulation",
    summary: "Dry-run a scenario against a runbook before anything touches production.",
    group: "Agents",
    keywords: ["dry run", "rehearse", "scenario", "test"],
  },
  {
    href: "/integrations",
    title: "MCP & integrations",
    summary: "Connect Claude, ChatGPT, or your own client to this workspace over MCP.",
    group: "Agents",
    keywords: ["mcp", "claude", "chatgpt", "oauth", "client", "server"],
  },
  {
    href: "/benchmarks",
    title: "Benchmarks",
    summary: "How the retrieval engine scores against the baseline.",
    group: "Agents",
    keywords: ["evaluation", "hcag", "metrics", "quality"],
  },

  {
    href: "/settings",
    title: "Settings",
    summary: "Workspace behaviour, models, and retrieval configuration.",
    group: "Admin",
    keywords: ["preferences", "config", "model"],
  },
  {
    href: "/account",
    title: "Account & people",
    summary: "Your identity, your workspaces, and who else is in this one.",
    group: "Admin",
    keywords: ["profile", "team", "members", "invite", "role", "logout"],
  },
  {
    href: "/keys",
    title: "API keys",
    summary: "Issue and revoke keys for programmatic access.",
    group: "Admin",
    keywords: ["token", "credentials", "api", "sdk"],
  },
  {
    href: "/admin",
    title: "Platform admin",
    summary: "Runtime status, importers, and memory maintenance.",
    group: "Admin",
    keywords: ["runtime", "maintenance", "repair", "importers", "debug"],
    adminOnly: true,
  },
];

export const GROUP_ORDER: DestinationGroup[] = [
  "Ask",
  "Knowledge",
  "Govern",
  "Agents",
  "Admin",
];

export const GROUP_BLURB: Record<DestinationGroup, string> = {
  Ask: "Get an answer, or hand work to an agent.",
  Knowledge: "What memory holds, and where it came from.",
  Govern: "What needs a person's judgement.",
  Agents: "The surfaces machines talk to.",
  Admin: "Who you are and how this workspace runs.",
};

export const PRIMARY_DESTINATIONS = DESTINATIONS.filter((item) => item.primary);

/* Dynamic routes cannot be listed one by one, so the title bar falls back to the
   nearest registered parent. `/runbooks/rb_12` is still "Runbooks". */
export function destinationFor(pathname: string): Destination | undefined {
  const exact = DESTINATIONS.find((item) => item.href === pathname);
  if (exact) return exact;
  return DESTINATIONS.filter((item) => item.href !== "/" && pathname.startsWith(`${item.href}/`))
    .sort((left, right) => right.href.length - left.href.length)
    .at(0);
}

export function titleFor(pathname: string): string {
  return destinationFor(pathname)?.title || "";
}

/* Ranked so an exact title match always wins over a keyword brush. Someone who
   types "graph" wants the graph, not every page that mentions one. */
export function searchDestinations(query: string, isAdmin: boolean): Destination[] {
  const allowed = DESTINATIONS.filter((item) => !item.adminOnly || isAdmin);
  const needle = query.trim().toLowerCase();
  if (!needle) return allowed;
  const scored = allowed
    .map((item) => ({ item, score: score(item, needle) }))
    .filter((entry) => entry.score > 0);
  scored.sort((left, right) => right.score - left.score);
  return scored.map((entry) => entry.item);
}

function score(item: Destination, needle: string): number {
  const title = item.title.toLowerCase();
  if (title === needle) return 100;
  if (title.startsWith(needle)) return 80;
  if (title.includes(needle)) return 60;
  if (item.href.includes(needle)) return 50;
  if (item.keywords?.some((keyword) => keyword.startsWith(needle))) return 40;
  if (item.keywords?.some((keyword) => keyword.includes(needle))) return 25;
  if (item.summary.toLowerCase().includes(needle)) return 10;
  return 0;
}
