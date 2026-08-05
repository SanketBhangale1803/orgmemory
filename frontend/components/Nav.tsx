"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import RunbookLogo from "@/components/RunbookLogo";

const domains = [
  { id: "home", label: "Home", href: "/workspace", paths: ["/workspace"] },
  { id: "add", label: "Add knowledge", href: "/ingest", paths: ["/connectors", "/ingest", "/jobs"] },
  { id: "ask", label: "Ask OrgMemory", href: "/ask", paths: ["/ask"] },
  { id: "work", label: "Memory Work", href: "/work", paths: ["/work"] },
  { id: "explore", label: "Explore", href: "/memories", paths: ["/memories", "/graph", "/profiles", "/projects", "/updates", "/conflicts"] },
  { id: "settings", label: "Settings", href: "/settings", paths: ["/settings", "/integrations", "/keys", "/account"] },
] as const;

const tabs: Record<string, { label: string; href: string }[]> = {
  add: [{label:"Add knowledge",href:"/ingest"},{label:"Connections",href:"/connectors"},{label:"Ingestion jobs",href:"/jobs"}],
  explore: [{label:"Memories",href:"/memories"},{label:"Memory Graph",href:"/graph"},{label:"Profiles",href:"/profiles"},{label:"Change Intelligence",href:"/updates"},{label:"Conflicts",href:"/conflicts"},{label:"Projects",href:"/projects"}],
  settings: [{label:"Settings",href:"/settings"},{label:"MCP & integrations",href:"/integrations"},{label:"API keys",href:"/keys"}],
};

function matches(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

export default function Nav({ user }: { user: any }) {
  const pathname = usePathname();
  const activeDomain = domains.find(domain => domain.paths.some(path => matches(pathname, path)));
  const activeTabs = activeDomain ? tabs[activeDomain.id] || [] : [];
  const workspace = user.workspaces?.find((item:any) => item.id === user.active_workspace_id);
  const initials = (user.display_name || user.email || "RB").split(/\s+/).map((part:string) => part[0]).join("").slice(0,2).toUpperCase();

  return <header className="app-header">
    <div className="primary-bar">
      <Link href="/workspace" className="brand" aria-label="OrgMemory workspace"><RunbookLogo inverted /></Link>
      <nav className="primary-nav" aria-label="Primary navigation">
        {domains.map(domain => <Link key={domain.id} href={domain.href} className={activeDomain?.id === domain.id ? "active" : ""}>{domain.label}</Link>)}
      </nav>
      <Link className="account-control" href="/account" title="Account and workspace"><span><small>{workspace?.name || "Workspace"}</small><strong>{user.display_name}</strong></span><i>{initials}</i></Link>
    </div>
    {activeTabs.length > 0 && <div className="context-bar"><div><span className="context-title">{activeDomain?.label}</span><nav aria-label={`${activeDomain?.label} sections`}>{activeTabs.map(tab => <Link key={tab.href} href={tab.href} className={matches(pathname, tab.href) ? "active" : ""}>{tab.label}</Link>)}</nav><span className="context-status"><span className="status-dot"/> Source-backed memory</span></div></div>}
  </header>;
}
