type WebMCPJSONSchema = Record<string, unknown>;

type WebMCPToolResult = {
  content: Array<{ type: "text"; text: string }>;
  structuredContent?: unknown;
};

type WebMCPTool = {
  name: string;
  title?: string;
  description: string;
  inputSchema?: WebMCPJSONSchema;
  annotations?: {
    readOnlyHint?: boolean;
    destructiveHint?: boolean;
    idempotentHint?: boolean;
    openWorldHint?: boolean;
    untrustedContentHint?: boolean;
  };
  execute: (
    input: Record<string, unknown>,
  ) => WebMCPToolResult | Promise<WebMCPToolResult>;
};

type WebMCPRegisteredTool = {
  name: string;
  title?: string;
  description: string;
  inputSchema?: string;
  origin?: string;
};

interface WebMCPModelContext extends EventTarget {
  registerTool(
    tool: WebMCPTool,
    options?: { signal?: AbortSignal; exposedTo?: string[] },
  ): Promise<void>;
  getTools?(options?: { fromOrigins?: string[] }): Promise<WebMCPRegisteredTool[]>;
}

interface Document {
  readonly modelContext?: WebMCPModelContext;
}
