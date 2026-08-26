export const ORGMEMORY_WEBMCP_TOOLS = [
  "list_orgmemory_spaces",
  "ask_orgmemory",
  "inspect_orgmemory_changes",
  "propose_repository_refresh",
  "list_orgmemory_approvals",
  "resolve_orgmemory_approval",
] as const;

export type OrgMemorySpace = {
  id: string;
  name: string;
  repository?: string;
};

export type OrgMemoryEvidence = {
  source_title: string;
  source_type: string;
  source_url?: string;
};

export type OrgMemoryWebMCPAnswer = {
  answer: string;
  answer_sufficient: boolean;
  answer_scope: string;
  resolved_subject?: string;
  searched_sources?: number;
  evidence: OrgMemoryEvidence[];
};

export type OrgMemoryChangeSet = {
  id: string;
  source_id: string;
  actor?: string;
  review_status?: string;
  created_at: string;
  added?: unknown[];
  updated?: unknown[];
  invalidated?: unknown[];
  conflicts?: unknown[];
  affected_artifacts?: unknown[];
  affected_skills?: unknown[];
};

export type OrgMemoryRefreshRequestResult = {
  files_scanned?: number;
  incremental?: { sources_changed?: number };
};

export type OrgMemoryRefreshRequest = {
  id: string;
  project_id: string;
  project_name?: string;
  repository: string;
  reason: string;
  status:
    | "pending_approval"
    | "denied"
    | "queued"
    | "running"
    | "succeeded"
    | "failed";
  requested_at: string;
  requested_by_id?: string;
  requested_by_name?: string;
  requested_by_email?: string;
  result?: OrgMemoryRefreshRequestResult;
  error?: string;
};

export type WebMCPActivity = {
  tool: (typeof ORGMEMORY_WEBMCP_TOOLS)[number];
  state: "running" | "complete" | "error";
  message?: string;
};

type RegistrationOptions = {
  spaces: OrgMemorySpace[];
  getActiveProjectId: () => string;
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
  resolveApproval?: (
    requestId: string,
    approved: boolean,
  ) => Promise<OrgMemoryRefreshRequest>;
  onActivity?: (activity: WebMCPActivity) => void;
};

export type WebMCPRegistration = {
  supported: boolean;
  toolCount: number;
  dispose: () => void;
};

const READ_ONLY = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;

const APPROVAL_REQUIRED_WRITE = {
  readOnlyHint: false,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: false,
} as const;

function toolResult(summary: string, structuredContent: unknown): WebMCPToolResult {
  return {
    content: [
      { type: "text", text: summary },
      { type: "text", text: JSON.stringify(structuredContent) },
    ],
    structuredContent,
  };
}

function stringInput(input: Record<string, unknown>, key: string): string {
  return typeof input[key] === "string" ? input[key].trim() : "";
}

function projectFor(
  input: Record<string, unknown>,
  spaces: OrgMemorySpace[],
  activeProjectId: string,
): OrgMemorySpace {
  const requested = stringInput(input, "project_id") || activeProjectId;
  const project = spaces.find((space) => space.id === requested);
  if (!project) {
    throw new Error(
      "Choose a project_id returned by list_orgmemory_spaces before using this tool.",
    );
  }
  return project;
}

function count(value: unknown[] | undefined): number {
  return Array.isArray(value) ? value.length : 0;
}

async function tracked<T>(
  tool: WebMCPActivity["tool"],
  onActivity: RegistrationOptions["onActivity"],
  run: () => Promise<T> | T,
): Promise<T> {
  onActivity?.({ tool, state: "running" });
  try {
    const value = await run();
    onActivity?.({ tool, state: "complete" });
    return value;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Tool execution failed";
    onActivity?.({ tool, state: "error", message });
    throw error;
  }
}

/**
 * Register the authenticated workspace as a browser-native Model Context
 * Provider. The page owns execution, so every call reuses its secure session
 * cookie and the same authorization checks as a human action in the UI.
 */
export async function registerOrgMemoryWebMCP(
  options: RegistrationOptions,
): Promise<WebMCPRegistration> {
  if (typeof document === "undefined" || !document.modelContext) {
    return { supported: false, toolCount: 0, dispose: () => undefined };
  }

  const controller = new AbortController();
  const modelContext = document.modelContext;
  const registration = { signal: controller.signal };

  const registrations = [
    modelContext.registerTool(
      {
        name: "list_orgmemory_spaces",
        title: "List OrgMemory spaces",
        description:
          "List the company-memory projects the signed-in person can access. Call this before choosing a project for another OrgMemory tool.",
        inputSchema: {
          type: "object",
          properties: {},
          additionalProperties: false,
        },
        annotations: READ_ONLY,
        execute: () =>
          tracked("list_orgmemory_spaces", options.onActivity, () => {
            const activeProjectId = options.getActiveProjectId();
            const payload = {
              active_project_id: activeProjectId,
              spaces: options.spaces.map(({ id, name, repository }) => ({
                project_id: id,
                name,
                repository: repository || undefined,
              })),
            };
            return toolResult(
              `${payload.spaces.length} authorized OrgMemory space${payload.spaces.length === 1 ? "" : "s"} available.`,
              payload,
            );
          }),
      },
      registration,
    ),
    modelContext.registerTool(
      {
        name: "ask_orgmemory",
        title: "Ask company memory",
        description:
          "Ask a question against current, permission-scoped company memory. The answer is shown in the OrgMemory workspace and returned with its source citations.",
        inputSchema: {
          type: "object",
          properties: {
            question: {
              type: "string",
              minLength: 3,
              maxLength: 4000,
              description: "The question to answer from company memory.",
            },
            project_id: {
              type: "string",
              description:
                "An authorized project ID from list_orgmemory_spaces. Defaults to the active project.",
            },
            scope: {
              type: "string",
              enum: ["workspace", "project"],
              description:
                "Search all authorized company memory or only the selected project. Defaults to workspace.",
            },
          },
          required: ["question"],
          additionalProperties: false,
        },
        annotations: READ_ONLY,
        execute: (input) =>
          tracked("ask_orgmemory", options.onActivity, async () => {
            const question = stringInput(input, "question");
            if (question.length < 3) throw new Error("question must contain at least 3 characters");
            const project = projectFor(
              input,
              options.spaces,
              options.getActiveProjectId(),
            );
            const scope = input.scope === "project" ? "project" : "workspace";
            const answer = await options.ask(question, project.id, scope);
            const payload = {
              project_id: project.id,
              project_name: project.name,
              scope,
              answer: answer.answer,
              answer_sufficient: answer.answer_sufficient,
              answer_scope: answer.answer_scope,
              resolved_subject: answer.resolved_subject,
              searched_sources: answer.searched_sources,
              evidence: (answer.evidence || []).map(
                ({ source_title, source_type, source_url }) => ({
                  title: source_title,
                  type: source_type,
                  url: source_url,
                }),
              ),
            };
            return toolResult(
              `${answer.answer}\n\nSources: ${payload.evidence.map((source) => source.title).join(", ") || "No source was sufficient."}`,
              payload,
            );
          }),
      },
      registration,
    ),
    modelContext.registerTool(
      {
        name: "inspect_orgmemory_changes",
        title: "Inspect recent memory changes",
        description:
          "Inspect recent source-backed memory changes for an authorized project, including additions, updates, invalidations, conflicts, and downstream artifacts needing review.",
        inputSchema: {
          type: "object",
          properties: {
            project_id: {
              type: "string",
              description:
                "An authorized project ID from list_orgmemory_spaces. Defaults to the active project.",
            },
            limit: {
              type: "integer",
              minimum: 1,
              maximum: 50,
              default: 10,
              description: "Maximum number of recent change sets to return.",
            },
          },
          additionalProperties: false,
        },
        annotations: READ_ONLY,
        execute: (input) =>
          tracked("inspect_orgmemory_changes", options.onActivity, async () => {
            const project = projectFor(
              input,
              options.spaces,
              options.getActiveProjectId(),
            );
            const requestedLimit = typeof input.limit === "number" ? input.limit : 10;
            const limit = Math.max(1, Math.min(50, Math.trunc(requestedLimit)));
            const changes = await options.inspectChanges(project.id, limit);
            const payload = {
              project_id: project.id,
              project_name: project.name,
              change_count: changes.length,
              changes: changes.map((change) => ({
                change_set_id: change.id,
                source_id: change.source_id,
                created_at: change.created_at,
                actor: change.actor,
                review_status: change.review_status,
                added: count(change.added),
                updated: count(change.updated),
                invalidated: count(change.invalidated),
                conflicts: count(change.conflicts),
                affected_artifacts: count(change.affected_artifacts),
                affected_skills: count(change.affected_skills),
              })),
            };
            const reviewCount = payload.changes.filter(
              (change) => change.review_status === "needs_review",
            ).length;
            return toolResult(
              `${changes.length} recent change set${changes.length === 1 ? "" : "s"} found for ${project.name}; ${reviewCount} need review.`,
              payload,
            );
          }),
      },
      registration,
    ),
    modelContext.registerTool(
      {
        name: "propose_repository_refresh",
        title: "Propose repository refresh",
        description:
          "Create an approval-required request to refresh an authorized GitHub repository when its OrgMemory evidence is stale or incomplete. This tool never refreshes the repository itself; a person must approve it in OrgMemory first.",
        inputSchema: {
          type: "object",
          properties: {
            project_id: {
              type: "string",
              description:
                "An authorized GitHub-backed project ID from list_orgmemory_spaces. Defaults to the active project.",
            },
            reason: {
              type: "string",
              minLength: 5,
              maxLength: 800,
              description:
                "Why a refresh is needed, such as stale commit evidence or a missing source.",
            },
          },
          required: ["reason"],
          additionalProperties: false,
        },
        annotations: APPROVAL_REQUIRED_WRITE,
        execute: (input) =>
          tracked("propose_repository_refresh", options.onActivity, async () => {
            const project = projectFor(input, options.spaces, options.getActiveProjectId());
            if (!project.repository) {
              throw new Error("Choose a GitHub-backed project before requesting a repository refresh.");
            }
            const reason = stringInput(input, "reason");
            if (reason.length < 5) throw new Error("reason must contain at least 5 characters");
            const request = await options.proposeRepositoryRefresh(project.id, reason);
            const payload = {
              refresh_request_id: request.id,
              project_id: project.id,
              project_name: project.name,
              repository: request.repository,
              reason: request.reason,
              status: request.status,
              next_step:
                "A person must approve or deny this request in OrgMemory before any repository refresh runs.",
            };
            return toolResult(
              `Repository refresh request for ${project.name} is ${request.status}. No refresh has run yet; it requires human approval.`,
              payload,
            );
          }),
      },
      registration,
    ),
    modelContext.registerTool(
      {
        name: "list_orgmemory_approvals",
        title: "List pending approvals",
        description:
          "List repository refresh requests that are waiting for a human approval decision in the authorized OrgMemory projects, including who requested each one and why.",
        inputSchema: {
          type: "object",
          properties: {
            project_id: {
              type: "string",
              description:
                "An authorized project ID from list_orgmemory_spaces. Defaults to showing every authorized project.",
            },
          },
          additionalProperties: false,
        },
        annotations: READ_ONLY,
        execute: (input) =>
          tracked("list_orgmemory_approvals", options.onActivity, async () => {
            const requested = stringInput(input, "project_id");
            if (requested && !options.spaces.some((space) => space.id === requested)) {
              throw new Error(
                "Choose a project_id returned by list_orgmemory_spaces before using this tool.",
              );
            }
            if (!options.listApprovals) {
              throw new Error("Approval tools are not available on this page.");
            }
            // The backend already scopes this list to what the signed-in person
            // may see and resolve; re-checking and re-filtering here keeps
            // unauthorized or cross-project rows out of the agent's payload.
            const fetched = requested
              ? await options.listApprovals(requested)
              : (
                  await Promise.all(
                    options.spaces.map((space) =>
                      options.listApprovals!(space.id).catch(() => []),
                    ),
                  )
                ).flat();
            const requests = requested
              ? fetched.filter((request) => request.project_id === requested)
              : fetched;
            const pending = requests.filter((request) => request.status === "pending_approval");
            const payload = {
              project_id: requested || undefined,
              pending_count: pending.length,
              resolved_recently: requests.length - pending.length,
              approvals: requests.map((request) => ({
                refresh_request_id: request.id,
                project_id: request.project_id,
                project_name: request.project_name,
                repository: request.repository,
                reason: request.reason,
                status: request.status,
                requested_by_name: request.requested_by_name,
                requested_by_email: request.requested_by_email,
                requested_at: request.requested_at,
              })),
            };
            return toolResult(
              pending.length
                ? `${pending.length} approval${pending.length === 1 ? "" : "s"} waiting, including ${pending
                    .slice(0, 3)
                    .map((request) => request.repository)
                    .join(", ")}. Use resolve_orgmemory_approval to decide one.`
                : "No approvals are waiting for a human decision.",
              payload,
            );
          }),
      },
      registration,
    ),
    modelContext.registerTool(
      {
        name: "resolve_orgmemory_approval",
        title: "Approve or deny a pending request",
        description:
          "Record a human approval decision on a pending OrgMemory repository refresh request. Approving queues the server-side GitHub ingest; denying closes it. This tool must only be used when the signed-in person has actually decided.",
        inputSchema: {
          type: "object",
          properties: {
            refresh_request_id: {
              type: "string",
              description:
                "The refresh_request_id of a pending approval from list_orgmemory_approvals.",
            },
            approved: {
              type: "boolean",
              description:
                "True records an approval and queues the repository refresh; false denies it.",
            },
          },
          required: ["refresh_request_id", "approved"],
          additionalProperties: false,
        },
        annotations: APPROVAL_REQUIRED_WRITE,
        execute: (input) =>
          tracked("resolve_orgmemory_approval", options.onActivity, async () => {
            if (!options.resolveApproval) {
              throw new Error("Approval decisions are not available on this page.");
            }
            const requestId = stringInput(input, "refresh_request_id");
            if (!requestId) throw new Error("refresh_request_id is required");
            const approved = input.approved === true;
            const request = await options.resolveApproval(requestId, approved);
            const payload = {
              refresh_request_id: request.id,
              project_id: request.project_id,
              project_name: request.project_name,
              repository: request.repository,
              reason: request.reason,
              requested_by_name: request.requested_by_name,
              status: request.status,
              next_step:
                request.status === "queued"
                  ? "The repository ingest was queued; memory will update when it completes."
                  : "The request stays pending until a person approves it.",
            };
            return toolResult(
              request.status === "queued"
                ? `Approved. The refresh of ${request.repository} is queued and will update company memory.`
                : `Decision recorded: ${request.status.replace(/_/g, " ")}.`,
              payload,
            );
          }),
      },
      registration,
    ),
  ];

  try {
    await Promise.all(registrations);
  } catch (error) {
    controller.abort();
    throw error;
  }

  return {
    supported: true,
    toolCount: ORGMEMORY_WEBMCP_TOOLS.length,
    dispose: () => controller.abort(),
  };
}
