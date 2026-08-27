"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  registerOrgMemoryWebMCP,
  type OrgMemoryChangeSet,
  type OrgMemoryRefreshRequest,
  type OrgMemorySpace,
  type OrgMemoryWebMCPAnswer,
  type WebMCPActivity,
} from "@/lib/webmcp";

type HookOptions = {
  enabled: boolean;
  spaces: OrgMemorySpace[];
  activeProjectId: string;
  ask: (
    question: string,
    projectId: string,
    scope: "workspace" | "project",
  ) => Promise<OrgMemoryWebMCPAnswer>;
  inspectChanges: (projectId: string, limit: number) => Promise<OrgMemoryChangeSet[]>;
  proposeRepositoryRefresh: (
    projectId: string,
    reason: string,
  ) => Promise<OrgMemoryRefreshRequest>;
  listApprovals?: (projectId: string) => Promise<OrgMemoryRefreshRequest[]>;
  canResolveApprovals?: boolean;
  resolveApproval?: (
    requestId: string,
    approved: boolean,
  ) => Promise<OrgMemoryRefreshRequest>;
};

export type WebMCPStatus = "idle" | "registering" | "ready" | "unsupported" | "error";

export function useOrgMemoryWebMCP(options: HookOptions) {
  const optionsRef = useRef(options);
  const [status, setStatus] = useState<WebMCPStatus>("idle");
  const [activity, setActivity] = useState<WebMCPActivity>();
  const [toolCount, setToolCount] = useState(0);
  optionsRef.current = options;

  const spacesKey = useMemo(
    () => options.spaces.map((space) => `${space.id}:${space.name}:${space.repository || ""}`).join("|"),
    [options.spaces],
  );

  useEffect(() => {
    if (!options.enabled) {
      setStatus("idle");
      setToolCount(0);
      return;
    }

    let current = true;
    let dispose: () => void = () => undefined;
    setStatus("registering");

    registerOrgMemoryWebMCP({
      spaces: optionsRef.current.spaces,
      getActiveProjectId: () => optionsRef.current.activeProjectId,
      ask: (...args) => optionsRef.current.ask(...args),
      inspectChanges: (...args) => optionsRef.current.inspectChanges(...args),
      proposeRepositoryRefresh: (...args) => optionsRef.current.proposeRepositoryRefresh(...args),
      listApprovals: optionsRef.current.listApprovals
        ? (...args) => optionsRef.current.listApprovals!(...args)
        : undefined,
      canResolveApprovals: optionsRef.current.canResolveApprovals,
      resolveApproval: optionsRef.current.resolveApproval
        ? (...args) => optionsRef.current.resolveApproval!(...args)
        : undefined,
      onActivity: (next) => {
        if (current) setActivity(next);
      },
    })
      .then((registration) => {
        if (!current) {
          registration.dispose();
          return;
        }
        dispose = registration.dispose;
        setStatus(registration.supported ? "ready" : "unsupported");
        setToolCount(registration.toolCount);
      })
      .catch(() => {
        if (current) setStatus("error");
      });

    return () => {
      current = false;
      dispose();
    };
  // A session can hydrate before its workspace role arrives. Re-register when
  // that role becomes known so an admin receives the decision tool, while a
  // member never does; server-side authorization remains the final boundary.
  }, [options.enabled, options.canResolveApprovals, spacesKey]);

  return { status, activity, toolCount };
}
