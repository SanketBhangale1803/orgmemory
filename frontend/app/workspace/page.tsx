"use client";

import { useEffect, useState } from "react";
import WorkspaceChat from "@/components/WorkspaceChat";
import { api } from "@/lib/api";

/* The workspace is the chat. Everything else — memories, graph, connectors,
   approvals — stays reachable, but nobody has to pass through a dashboard to
   ask their company a question. */
export default function Workspace() {
  const [user, setUser] = useState<any>();

  useEffect(() => {
    api("/api/auth/me").then(setUser).catch(() => setUser({}));
  }, []);

  return <WorkspaceChat user={user} />;
}
