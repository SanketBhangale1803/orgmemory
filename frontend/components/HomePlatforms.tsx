"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Platform = {
  provider: string;
  label: string;
  category: string;
  role: string;
  status: string;
  memory: string[];
};

/* Mirrors the backend catalog so the grid renders identically before the
   request resolves and if the API is unreachable. */
const fallback: Platform[] = [
  { provider: "github", label: "GitHub", category: "Code & delivery", role: "source", status: "live", memory: ["code", "commits", "pull requests", "issues", "reviews"] },
  { provider: "slack", label: "Slack", category: "Conversations", role: "source_and_channel", status: "live", memory: ["messages", "threads", "decisions", "approved replies"] },
  { provider: "uploads", label: "Files & exports", category: "Knowledge", role: "source", status: "live", memory: ["documents", "reports", "exports", "incident notes"] },
  { provider: "google_drive", label: "Google Drive", category: "Google Workspace", role: "source", status: "next", memory: ["Docs", "Sheets", "Slides", "shared files"] },
  { provider: "gmail", label: "Gmail", category: "Google Workspace", role: "source_and_channel", status: "next", memory: ["threads", "decisions", "attachments"] },
  { provider: "microsoft_365", label: "Microsoft 365", category: "Microsoft", role: "source", status: "next", memory: ["SharePoint", "Word", "Excel", "OneDrive"] },
  { provider: "teams", label: "Microsoft Teams", category: "Microsoft", role: "source_and_channel", status: "next", memory: ["chats", "channels", "meetings"] },
  { provider: "outlook", label: "Outlook", category: "Microsoft", role: "source_and_channel", status: "next", memory: ["mail", "threads", "attachments"] },
  { provider: "atlassian", label: "Atlassian", category: "Work management", role: "source", status: "next", memory: ["Jira issues", "Confluence pages", "comments"] },
  { provider: "notion", label: "Notion", category: "Knowledge", role: "source", status: "planned", memory: ["pages", "databases", "comments"] },
  { provider: "linear", label: "Linear", category: "Work management", role: "source", status: "planned", memory: ["issues", "projects", "comments"] },
  { provider: "clickup", label: "ClickUp", category: "Work management", role: "source", status: "planned", memory: ["tasks", "docs", "comments"] },
  { provider: "buzz", label: "Buzz", category: "Conversations", role: "source_and_channel", status: "planned", memory: ["messages", "threads", "approved replies"] },
  { provider: "yahoo_mail", label: "Yahoo Mail", category: "Conversations", role: "source_and_channel", status: "planned", memory: ["mail", "threads", "attachments"] },
  { provider: "mcp", label: "MCP", category: "Agent surfaces", role: "delivery", status: "live", memory: ["Cursor", "Claude", "Codex", "VS Code agents"] },
  { provider: "api_sdk_cli", label: "API, Python & CLI", category: "Agent surfaces", role: "delivery", status: "live", memory: ["context envelopes", "swarm traces", "cited answers"] },
];

/* Grouped by what a visitor can actually do today rather than by vendor family:
   one-item vendor groups left most of each row empty, and "can I connect this
   now?" is the question the section exists to answer. */
const groups = [
  { status: "live", title: "Live today", note: "Connect these in a few minutes." },
  { status: "next", title: "Next adapters", note: "In build, in this order." },
  { status: "planned", title: "On the roadmap", note: "Published so you can plan around it." },
];

const statusLabel: Record<string, string> = {
  live: "Connect now",
  next: "Next adapter",
  planned: "On the roadmap",
};

const marks: Record<string, string> = {
  github: "GH",
  slack: "SL",
  uploads: "FX",
  google_drive: "GD",
  gmail: "GM",
  microsoft_365: "MS",
  teams: "MT",
  outlook: "OL",
  atlassian: "AT",
  notion: "NO",
  linear: "LN",
  clickup: "CU",
  buzz: "BZ",
  yahoo_mail: "YM",
  mcp: "MCP",
  api_sdk_cli: "API",
};

function monogram(provider: string, label: string) {
  if (marks[provider]) return marks[provider];
  const words = label.replace(/[&,]/g, "").split(/\s+/).filter(Boolean);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export default function HomePlatforms() {
  const [platforms, setPlatforms] = useState<Platform[]>(fallback);

  useEffect(() => {
    api<{ platforms: Platform[] }>("/api/platforms")
      .then((payload) => {
        if (payload.platforms?.length) setPlatforms(payload.platforms);
      })
      .catch(() => undefined);
  }, []);

  const rendered = groups
    .map((group) => ({ ...group, items: platforms.filter((item) => item.status === group.status) }))
    .filter((group) => group.items.length > 0);
  const liveCount = platforms.filter((item) => item.status === "live").length;

  return (
    <>
      <div className="plat-groups">
        {rendered.map((group, groupIndex) => (
          <section className="plat-group reveal" style={{ ["--i" as string]: groupIndex }} key={group.status}>
            <h3>{group.title}<em>{group.note}</em></h3>
            <div className="plat-row">
              {group.items.map((item) => (
                <article
                  className={`plat-card ${item.status === "live" ? "is-live" : ""}`}
                  key={item.provider}
                >
                  <header>
                    <span>{monogram(item.provider, item.label)}</span>
                    <div>
                      <strong>{item.label}</strong>
                      <small>{item.category}</small>
                    </div>
                  </header>
                  <p>{item.memory.slice(0, 4).join(" · ")}</p>
                  <span className={`plat-state ${item.status === "live" ? "live" : ""}`}>
                    <i />
                    {statusLabel[item.status] || item.status}
                  </span>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
      <div className="plat-foot reveal">
        <span>
          <strong>{liveCount} surfaces are live today.</strong> The rest are published as a roadmap,
          not as buttons that pretend to work.
        </span>
        <span>Every source keeps its own permissions. Memory never outlives its evidence.</span>
      </div>
    </>
  );
}
