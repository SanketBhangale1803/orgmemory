"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import ChatBackBar from "@/components/ChatBackBar";
import Nav from "@/components/Nav";
import { RunbookMark } from "@/components/RunbookLogo";
import { api } from "@/lib/api";

const SECURING_MIN_MS = 450;

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLanding = pathname === "/";
  const isDocs = pathname === "/docs" || pathname.startsWith("/docs/");
  const isPublic = isLanding || isDocs || pathname === "/login";
  const isLogin = pathname === "/login";
  const isChat = pathname === "/workspace";
  // Pages the chat links to directly. They keep the chat's slim chrome so the
  // "add a source" round trip never drops anyone into the older navigation.
  const chatSatellites: Record<string, string> = { "/ingest": "Add knowledge" };
  const satelliteTitle = chatSatellites[pathname];
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
  if (satelliteTitle) return <div className="om-home ws-satellite"><ChatBackBar user={user} title={satelliteTitle} /><main>{children}</main></div>;
  return <div className="shell"><Nav user={user}/><main className="main">{children}</main></div>;
}
