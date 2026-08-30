import type { Metadata } from "next";
import Link from "next/link";
import CodeBlock from "@/components/CodeBlock";
import PublicNav from "@/components/PublicNav";

export const metadata: Metadata = {
  title: "Docs — OrgMemory",
  description:
    "Build source-backed organizational memory into agents with OrgMemory's API, Python SDK, CLI, and context swarm.",
};

const sections = [
  ["quickstart", "Quickstart"],
  ["authentication", "Authentication"],
  ["models", "Model providers"],
  ["connectors", "Connectors"],
  ["python-sdk", "Python SDK"],
  ["cli", "CLI"],
  ["context-swarm", "Context swarm"],
  ["api", "Core API"],
  ["envelopes", "Context envelopes"],
  ["mcp", "MCP"],
  ["security", "Security"],
] as const;

const install = `cp .env.example .env
make runbook

# In another terminal, install the SDK + CLI.
make sdk-install`;

const pythonExample = `from orgmemory import OrgMemory

memory = OrgMemory(
    base_url="http://localhost:8000",
    api_key="om_live_..."
)

context = memory.ask(
    project_id="prj_platform",
    query="What changed in checkout, and why?"
)

print(context.answer)
print(context.compiled_context)

# Pass the source-backed context to any model or agent.
agent.run(context.compiled_context)`;

const cliExample = `export ORGMEMORY_API_URL=http://localhost:8000
export ORGMEMORY_API_KEY=om_live_...

orgmemory health
orgmemory projects
orgmemory ask prj_platform "What changed in checkout, and why?"
orgmemory ask prj_platform "Which incidents mention Redis?" --json`;

const curlExample = `curl -X POST "$ORGMEMORY_API_URL/api/ask" \\
  -H "Authorization: Bearer $ORGMEMORY_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "project_id": "prj_platform",
    "query": "What changed in checkout, and why?",
    "model": "claude",
    "token_budget": 8000
  }'`;

const ingestExample = `orgmemory ingest prj_platform \\
  --file ./incident-review.md \\
  --source-type doc \\
  --title "Checkout incident review"

# Or send inline content
orgmemory ingest prj_platform \\
  --content "Release 48 moved checkout to the new ledger." \\
  --source-type other`;

const swarmResponse = `{
  "run_id": "swarm_01J...",
  "status": "completed",
  "specialists": {
    "activation": "ranked candidate memories",
    "graph": "traversed related entities and decisions",
    "temporal": "resolved what was true at query time"
  },
  "compiler": "deduplicated, scoped context with evidence"
}`;

const apiRows = [
  ["GET", "/api/health", "Check API and dependency health."],
  ["GET", "/api/projects", "List projects visible to the caller."],
  ["POST", "/api/projects", "Create a project memory boundary."],
  ["POST", "/api/ingest/upload", "Add a document or source payload."],
  ["POST", "/api/ask", "Compile evidence and answer a question."],
  ["GET", "/api/models", "List GPT, Claude, Gemini, Grok, and Kimi readiness."],
  ["GET", "/api/connectors/catalog", "List live and planned company-memory sources."],
  ["GET", "/api/memory/units", "Inspect retrievable memory units."],
  ["GET", "/api/memory/graph/summary", "Inspect the organizational graph."],
  ["GET", "/api/memory/context/:id", "Read a compiled context envelope."],
  ["GET", "/api/memory/swarm/:runId", "Inspect a context-swarm trace."],
] as const;

export default function DocsPage() {
  return (
    <main className="brain-site om-site docs-site">
      <PublicNav compact />

      <div className="docs-layout">
        <aside className="docs-sidebar" aria-label="Documentation sections">
          <p>Documentation</p>
          <nav>
            {sections.map(([id, label]) => (
              <a key={id} href={`#${id}`}>
                {label}
              </a>
            ))}
          </nav>
          <div className="docs-sidebar__signal">
            <span aria-hidden="true" />
            Local-first quickstart
          </div>
        </aside>

        <article className="docs-content">
          <header className="docs-hero">
            <div className="om-eyebrow">
              <span />
              Developer documentation
            </div>
            <h1>
              Give your agents
              <br />
              <em>institutional memory.</em>
            </h1>
            <p>
              Connect company knowledge, retrieve the right evidence, and compile
              it into a context envelope your agents can trust.
            </p>
            <div className="docs-hero__actions">
              <a className="om-button" href="#quickstart">
                Start building
                <span aria-hidden="true">↘</span>
              </a>
              <Link className="om-button ghost" href="/workspace">
                Open workspace
              </Link>
            </div>
          </header>

          <section id="quickstart" className="docs-section">
            <div className="docs-kicker">01 / Quickstart</div>
            <h2>From zero to source-backed context.</h2>
            <p className="docs-lede">
              Start the API and workspace locally, create a project, then add
              knowledge through the UI, CLI, or HTTP API.
            </p>
            <CodeBlock label="Terminal" language="bash">
              {install}
            </CodeBlock>
            <div className="docs-note">
              <strong>Default services</strong>
              <span>
                API at <code>http://localhost:8000</code> · Workspace at{" "}
                <code>http://localhost:3000</code>
              </span>
            </div>
          </section>

          <section id="authentication" className="docs-section">
            <div className="docs-kicker">02 / Authentication</div>
            <h2>Work identity for people. Scoped keys for agents.</h2>
            <p>
              People can sign in with Google, GitHub, or a passwordless email
              code. SDK, CLI, MCP, and server-side agents use a workspace-scoped
              OrgMemory API key as a bearer token.
            </p>
            <CodeBlock label="Browser sign-in providers" language="bash">
              {`# GitHub OAuth app
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/github/callback

# Google OAuth web client
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# Passwordless email in production
EMAIL_AUTH_ENABLED=true
EMAIL_FROM=memory@company.com
SMTP_HOST=smtp.company.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...`}
            </CodeBlock>
            <div className="docs-note">
              <strong>GitHub fix</strong>
              <span>
                The GitHub button is enabled only when both credentials exist.
                Add the callback URL above to the OAuth app, update <code>.env</code>,
                then restart the backend.
              </span>
            </div>
            <CodeBlock label=".env" language="bash">
              {`ORGMEMORY_API_URL=https://memory.example.com
ORGMEMORY_API_KEY=om_live_...`}
            </CodeBlock>
          </section>

          <section id="models" className="docs-section">
            <div className="docs-kicker">03 / Model providers</div>
            <h2>One company context. Your choice of model.</h2>
            <p>
              OrgMemory retrieves, scopes, and compiles the evidence before a
              model sees it. Configure any combination of GLM, GPT, Claude,
              Gemini, Grok, and Kimi. If no model key is present, source-backed
              deterministic answer paths remain available.
            </p>
            <CodeBlock label="Model configuration" language="bash">
              {`OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514
GOOGLE_API_KEY=
GEMINI_MODEL=gemini-3.6-flash
OPENROUTER_API_KEY=
GLM_MODEL=z-ai/glm-5.3-flash
GLM_BASE_URL=https://openrouter.ai/api/v1
XAI_API_KEY=
GROK_MODEL=grok-4.5
KIMI_API_KEY=
KIMI_MODEL=kimi-k2.6

ORG_MEMORY_DEFAULT_MODEL_PROVIDER=glm`}
            </CodeBlock>
          </section>

          <section id="connectors" className="docs-section">
            <div className="docs-kicker">04 / Connectors</div>
            <h2>Make capability status explicit.</h2>
            <p>
              GitHub, Slack, uploads, the API, Python SDK, CLI, and MCP are live.
              Google Workspace, Gmail, Microsoft 365, Teams, Outlook, and
              Atlassian are the next adapter layer. The catalog endpoint exposes
              the same status shown in the workspace, so a planned integration
              is never presented as connected.
            </p>
            <div className="docs-object-grid">
              <div><code>live</code><span>Real authorization and ingestion or delivery path.</span></div>
              <div><code>next</code><span>Prioritized adapter; visible, but no fake connect action.</span></div>
              <div><code>planned</code><span>Roadmap source with a defined memory contract.</span></div>
              <div><code>source_and_channel</code><span>Can ingest a conversation and return an approved reply.</span></div>
            </div>
          </section>

          <section id="python-sdk" className="docs-section">
            <div className="docs-kicker">05 / Python SDK</div>
            <h2>Context assembly, typed in Python.</h2>
            <p>
              Install the SDK from this repository while it is in local
              development. The synchronous and asynchronous clients expose the
              same OrgMemory primitives.
            </p>
            <CodeBlock label="Install" language="bash">
              {`python -m pip install -e ./python_sdk`}
            </CodeBlock>
            <CodeBlock label="agent.py" language="python">
              {pythonExample}
            </CodeBlock>
          </section>

          <section id="cli" className="docs-section">
            <div className="docs-kicker">06 / CLI</div>
            <h2>Inspect memory from your terminal.</h2>
            <p>
              The CLI ships with the Python SDK. Use it to query projects,
              ingest sources, inspect graph state, and review context-swarm
              runs.
            </p>
            <CodeBlock label="Query" language="bash">
              {cliExample}
            </CodeBlock>
            <CodeBlock label="Ingest" language="bash">
              {ingestExample}
            </CodeBlock>
          </section>

          <section id="context-swarm" className="docs-section docs-section--swarm">
            <div className="docs-kicker">07 / Context swarm</div>
            <h2>Specialists forage. One compiler decides.</h2>
            <p>
              A query activates a small ecosystem of retrieval specialists.
              Each searches a different memory surface—semantic candidates,
              graph relationships, and temporal state. A compiler agent
              deduplicates their findings, applies scope, and emits one bounded
              context envelope.
            </p>
            <div className="docs-flow" aria-label="Context swarm pipeline">
              <span>Query</span>
              <i>→</i>
              <span>Activation</span>
              <span>Graph</span>
              <span>Temporal</span>
              <i>→</i>
              <span className="docs-flow__final">Compiler</span>
            </div>
            <CodeBlock label="Swarm trace" language="json">
              {swarmResponse}
            </CodeBlock>
          </section>

          <section id="api" className="docs-section">
            <div className="docs-kicker">08 / Core API</div>
            <h2>A small surface for a large memory.</h2>
            <CodeBlock label="Ask with HTTP" language="bash">
              {curlExample}
            </CodeBlock>
            <div className="docs-api-table">
              {apiRows.map(([method, path, description]) => (
                <div className="docs-api-row" key={`${method}-${path}`}>
                  <code className={`docs-method docs-method--${method.toLowerCase()}`}>
                    {method}
                  </code>
                  <code>{path}</code>
                  <span>{description}</span>
                </div>
              ))}
            </div>
          </section>

          <section id="envelopes" className="docs-section">
            <div className="docs-kicker">09 / Context envelopes</div>
            <h2>The answer is not the artifact.</h2>
            <p>
              Every ask returns an answer plus its compiled context, evidence,
              retrieval diagnostics, and a durable context-envelope identifier.
              Your agent can consume the context while your product keeps the
              provenance.
            </p>
            <div className="docs-object-grid">
              <div>
                <code>answer</code>
                <span>Grounded synthesis for the current query.</span>
              </div>
              <div>
                <code>compiled_context</code>
                <span>Bounded context ready for a model call.</span>
              </div>
              <div>
                <code>evidence</code>
                <span>Source references and relevance metadata.</span>
              </div>
              <div>
                <code>context_envelope.id</code>
                <span>Durable handle for replay and inspection.</span>
              </div>
            </div>
          </section>

          <section id="mcp" className="docs-section">
            <div className="docs-kicker">10 / MCP</div>
            <h2>Memory for tool-using agents.</h2>
            <p>
              OrgMemory includes an MCP server so compatible assistants can ask,
              ingest, browse the graph, and work with memory as native tools.
            </p>
            <CodeBlock label="Run the MCP server" language="bash">
              {`make mcp`}
            </CodeBlock>
          </section>

          <section id="security" className="docs-section">
            <div className="docs-kicker">11 / Security</div>
            <h2>Retrieval respects the caller.</h2>
            <p>
              Project boundaries, bearer authentication, and source metadata
              travel through retrieval. Keep API keys server-side, use a
              separate key per environment, and put the API behind TLS outside
              local development.
            </p>
            <div className="docs-checks">
              <span>✓ Scope before synthesis</span>
              <span>✓ Evidence on every answer</span>
              <span>✓ Inspectable swarm traces</span>
              <span>✓ Durable context envelopes</span>
            </div>
          </section>

          <footer className="docs-footer">
            <span>Ready to wire memory into your agent?</span>
            <a href="#quickstart">Back to quickstart ↑</a>
          </footer>
        </article>

        <aside className="docs-toc" aria-label="On this page">
          <p>On this page</p>
          {sections.slice(0, 6).map(([id, label]) => (
            <a key={id} href={`#${id}`}>
              {label}
            </a>
          ))}
        </aside>
      </div>
    </main>
  );
}
