"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const groups = [
  ["Workspace", [["Login", "/login", "◉"], ["Overview", "/", "▦"], ["Projects", "/projects", "◇"], ["Repo Graph", "/graph", "◎"], ["Ask Runbook", "/ask", "⌕"], ["Runbooks", "/runbooks", "≡"]]],
  ["Knowledge", [["Connectors", "/connectors", "⊕"], ["Ingest", "/ingest", "↥"], ["Ingestion Jobs", "/jobs", "↻"], ["Runbook Reliability", "/reliability", "◈"], ["Runbook Drift", "/drift", "≉"], ["Simulation", "/simulation", "▷"]]],
  ["Control", [["Approvals", "/approvals", "✓"], ["Audit log", "/audit", "◷"], ["Admin & security", "/admin", "▣"]]],
  ["Platform", [["MCP & integrations", "/integrations", "⌘"], ["API keys", "/keys", "⚿"], ["Benchmark Reports", "/benchmarks", "∿"], ["Settings", "/settings", "⚙"]]],
] as const;

export default function Nav() {
  const pathname = usePathname();
  return <aside className="sidebar">
    <div className="brand"><span className="mark">R</span><span>Runbook</span></div>
    {groups.map(([label, links]) => <div key={label}>
      <div className="nav-label">{label}</div>
      {links.map(([name, href, icon]) => <Link key={href} href={href} className={`nav-link ${pathname === href || (href !== "/" && pathname.startsWith(href)) ? "active" : ""}`}>
        <span className="nav-icon">{icon}</span><span>{name}</span>
      </Link>)}
    </div>)}
    <div className="sidebar-footer">Evidence-grounded memory<br/>Approval-gated execution</div>
  </aside>;
}
