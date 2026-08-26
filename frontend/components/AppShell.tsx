"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import ChatBackBar from "@/components/ChatBackBar";
import Nav from "@/components/Nav";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";

const SECURING_MIN_MS = 450;

/* One navigation model: the chat is home, and every other page is its satellite
   carrying the same slim bar. The legacy multi-domain header only survives as a
   fallback for routes that have not been given a title yet. */
const chatSatellites: Record<string, string> = {
  "/ingest": "Add knowledge",
  "/connectors": "Connections",
  "/jobs": "Ingestion jobs",
  "/ask": "Ask OrgMemory",
  "/work": "Memory work",
  "/approvals": "Approvals",
  "/memories": "Memories",
  "/graph": "Memory graph",
  "/profiles": "Profiles",
  "/projects": "Memory spaces",
  "/updates": "Change intelligence",
  "/conflicts": "Conflicts",
  "/settings": "Settings",
  "/integrations": "MCP & integrations",
  "/keys": "API keys",
  "/account": "Account",
  "/audit": "Audit log",
  "/benchmarks": "Benchmarks",
  "/drift": "Drift checks",
  "/simulation": "Simulation",
  "/runbooks": "Runbooks",
  "/reliability": "Reliability",
  "/admin": "Platform admin",
};

function satelliteTitle(pathname: string): string {
  if (chatSatellites[pathname]) return chatSatellites[pathname];
  if (pathname.startsWith("/runbooks/")) return "Runbook";
  if (pathname.startsWith("/reliability/")) return "Reliability";
  if (pathname.startsWith("/updates/")) return "Change intelligence";
  return "";
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLanding = pathname === "/";
  const isDocs = pathname === "/docs" || pathname.startsWith("/docs/");
  const isPublic = isLanding || isDocs || pathname === "/login";
  const isLogin = pathname === "/login";
  const isChat = pathname === "/workspace";
  const title = isChat ? "" : satelliteTitle(pathname);
  const [user, setUser] = useState<any>();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (isLanding) {
      setReady(true);
      return;
    }
    let current = true;
    let securingTimer: number | undefined;
    const securingStartedAt = Date.now();
    api("/api/auth/me")
      .then((principal) => {
        if (!current) return;
        if (isLogin) {
          router.replace("/workspace");
          return;
        }
        const remaining = Math.max(0, SECURING_MIN_MS - (Date.now() - securingStartedAt));
        securingTimer = window.setTimeout(() => {
          if (!current) return;
          setUser(principal);
          setReady(true);
        }, remaining);
      })
      .catch(() => {
        if (!current) return;
        setReady(true);
        if (!isPublic) router.replace("/login");
      });
    return () => {
      current = false;
      if (securingTimer !== undefined) window.clearTimeout(securingTimer);
    };
  }, [isLanding, isPublic, isLogin, router]);

  if (isPublic) return <>{children}</>;
  if (!ready || !user) return <div className="auth-loading"><RunbookMark /><div><p>Opening your memory…</p><span>Loading authorized company context</span></div><div className="secure-progress" aria-hidden="true"><i /></div></div>;
  // The chat carries its own minimal chrome. Wrapping it in the multi-domain
  // header would put the mechanics back on screen it was built to remove.
  if (isChat) return <>{children}</>;
  if (title) return <div className="om-home ws-satellite"><ChatBackBar user={user} title={title} /><main>{children}</main></div>;
  return <div className="shell"><Nav user={user}/><main className="main">{children}</main></div>;
}
