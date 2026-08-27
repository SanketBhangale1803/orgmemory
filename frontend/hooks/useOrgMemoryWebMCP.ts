"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  registerOrgMemoryWebMCP,
  type OrgMemoryChangeSet,
  type OrgMemoryProposal,
  type OrgMemoryProposalInput,
  type OrgMemoryRefreshRequest,
  type OrgMemoryRelatedEntry,
  type OrgMemoryRunbook,
  type OrgMemoryServiceContextEntry,
  type OrgMemorySpace,
  type OrgMemoryUnit,
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
  searchMemory: (
    projectId: string,
    query: string,
    type?: string,
    limit?: number,
  ) => Promise<OrgMemoryUnit[]>;
  getMemory: (memoryId: string) => Promise<OrgMemoryUnit>;
  getRelatedMemories: (memoryId: string) => Promise<OrgMemoryRelatedEntry[]>;
  listIncidents: (projectId: string, service?: string) => Promise<OrgMemoryUnit[]>;
  findRunbooks: (service: string, issue?: string) => Promise<OrgMemoryRunbook[]>;
  getServiceContext: (service: string) => Promise<OrgMemoryServiceContextEntry[]>;
  listDecisions: (projectId: string, limit?: number) => Promise<OrgMemoryUnit[]>;
  proposeMemory: (input: OrgMemoryProposalInput) => Promise<OrgMemoryProposal>;
  listProposals?: () => Promise<OrgMemoryProposal[]>;
  canResolveProposals?: boolean;
  resolveProposal?: (proposalId: string, approved: boolean) => Promise<OrgMemoryProposal>;
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
      searchMemory: (...args) => optionsRef.current.searchMemory(...args),
      getMemory: (...args) => optionsRef.current.getMemory(...args),
      getRelatedMemories: (...args) => optionsRef.current.getRelatedMemories(...args),
      listIncidents: (...args) => optionsRef.current.listIncidents(...args),
      findRunbooks: (...args) => optionsRef.current.findRunbooks(...args),
      getServiceContext: (...args) => optionsRef.current.getServiceContext(...args),
      listDecisions: (...args) => optionsRef.current.listDecisions(...args),
      proposeMemory: (...args) => optionsRef.current.proposeMemory(...args),
      listProposals: optionsRef.current.listProposals
        ? (...args) => optionsRef.current.listProposals!(...args)
        : undefined,
      canResolveProposals: optionsRef.current.canResolveProposals,
      resolveProposal: optionsRef.current.resolveProposal
        ? (...args) => optionsRef.current.resolveProposal!(...args)
        : undefined,
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
  // that role becomes known so an admin receives the decision tools, while a
  // member never does; server-side authorization remains the final boundary.
  }, [options.enabled, options.canResolveApprovals, options.canResolveProposals, spacesKey]);

  return { status, activity, toolCount };
}
