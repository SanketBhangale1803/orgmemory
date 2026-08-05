import Link from "next/link";
import type { CSSProperties } from "react";
import HomeChat from "@/components/HomeChat";
import HomeNav from "@/components/HomeNav";
import HomePlatforms from "@/components/HomePlatforms";
import Reveal from "@/components/Reveal";
import RunbookLogo, { RunbookMark } from "@/components/RunbookLogo";

const swarmPoints = [
  [
    "01",
    "One subagent per branch, not one search per question",
    "A large company is too wide for a single retrieval pass. OrgMemory splits the memory graph into branches and gives each one its own scout, so a hundred branches are explored at once instead of in sequence.",
  ],
  [
    "02",
    "Graph foragers follow meaning, not similarity",
    "Scouts walk services, owners, decisions, deployments, and code — the relationships a text search cannot see. The path they took is kept, so you can audit why a fact was included.",
  ],
  [
    "03",
    "Truth historians resolve what is still true",
    "Companies contradict themselves over time. A historian separates the current answer from the superseded one and records the disagreement instead of averaging it away.",
  ],
  [
    "04",
    "One compiler, one envelope",
    "Findings are deduplicated and compressed into a single token-bounded context envelope with citations attached — the exact input the model receives, saved and inspectable.",
  ],
];

const loopSteps = [
  ["Ask anywhere", "A question can start on the web, in a Slack or Teams thread, or from an agent inside your IDE. Same brain, same permissions."],
  ["Understand first", "OrgMemory reads the diff, the discussion, the decision, and the deployment history — not the commit message alone."],
  ["Act with a boundary", "Safe investigation continues on its own. Anything that changes your systems becomes a scoped, reviewable approval request."],
  ["Remember the result", "The answer, the approval, and the outcome all become new source-linked memory. The next person never re-derives it."],
];

export default function HomePage() {
  return (
    <main className="om-home">
      <Reveal />
      <div className="home-aura" aria-hidden="true"><i /><i /></div>
      <HomeNav />

      <section className="home-hero">
        <div className="home-wrap">
          <span className="home-eyebrow"><i /> The operating brain for your company</span>
          <h1>Your company already knows the answer.<br /><em>Now everyone can find it.</em></h1>
          <p>
            It is just scattered across code, chats, documents, tickets, inboxes, and people.
            OrgMemory gathers that evidence into one living company brain — then gives every
            employee and every agent the context to actually solve the problem.
          </p>
          <div className="home-hero-trust">
            <span><i /> Sources stay cited</span>
            <span><i /> Permissions stay intact</span>
            <span><i /> Actions wait for approval</span>
          </div>
        </div>
      </section>

      <HomeChat />

      <section className="home-section" id="connect">
        <div className="home-wrap">
          <div className="plat-head reveal">
            <div>
              <span className="home-eyebrow"><i /> Connect where the work already happens</span>
              <h2 className="home-h2">Every place your company<br />keeps its memory.</h2>
            </div>
            <p className="home-lede">
              Start in the web app and connect what your team already uses — GitHub and Slack are
              live today, with Google Workspace, Microsoft 365, and Atlassian next. OrgMemory then
              carries one consistent context back into all of them.
            </p>
          </div>
          <HomePlatforms />
        </div>
      </section>

      <section className="home-dark" id="swarm">
        <div className="home-wrap">
          <span className="home-eyebrow"><i /> Context activation swarm</span>
          <h2 className="home-h2">Retrieval is a team,<br />not a lookup.</h2>
          <p className="home-lede">
            Most memory products embed everything and hope the nearest neighbour is right.
            OrgMemory sends specialists into the graph, lets them disagree, and compiles what
            survives.
          </p>

          <div className="swarm-story">
            <ul className="swarm-points">
              {swarmPoints.map(([code, title, copy]) => (
                <li key={code}>
                  <span>{code}</span>
                  <div>
                    <strong>{title}</strong>
                    <p>{copy}</p>
                  </div>
                </li>
              ))}
            </ul>

            <div className="swarm-viz" aria-hidden="true">
              <div className="viz-node">
                <small>Question</small>
                <strong>Why is the website down?</strong>
              </div>
              <div className="viz-fan">
                {[
                  ["Scout · GitHub", "11 candidates"],
                  ["Scout · Slack", "6 threads"],
                  ["Forager · graph", "9 edges"],
                  ["Historian", "1 conflict"],
                ].map(([name, result], index) => (
                  <div className="viz-branch" style={{ ["--b" as string]: index } as CSSProperties} key={name}>
                    <i />
                    <b>{name}</b>
                    <span>{result}</span>
                  </div>
                ))}
              </div>
              <div className="viz-node final">
                <small>Compiled context envelope</small>
                <strong>14 cited chunks · 3,842 tokens</strong>
              </div>
              <div className="viz-meta">
                <span><i /> Authorized only</span>
                <span><i /> Deduplicated</span>
                <span><i /> Time-aware</span>
                <span><i /> Reproducible</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-wrap">
          <div className="story-grid">
            <div className="reveal">
              <span className="home-eyebrow"><i /> A semantic layer above raw activity</span>
              <h2 className="home-h2">A commit message is a hint.<br />The history is the truth.</h2>
              <p className="home-lede">
                Commit messages are empty, misleading, or written in a hurry. OrgMemory never treats
                one as fact. It reads the diff, the pull request, the issue it closed, the decision
                behind it, and the deployment state — then records what actually changed.
              </p>
              <p style={{ marginTop: 24 }}>
                <Link className="home-link" href="/docs#semantic-memory">
                  How semantic change memory works <span aria-hidden="true">→</span>
                </Link>
              </p>
            </div>

            <div className="story-card reveal">
              <header><span>change · checkout-api</span><em>understood, not copied</em></header>
              <div className="story-block weak">
                <span>What the commit said</span>
                <strong>&quot;updates&quot;</strong>
                <em>weak signal</em>
              </div>
              <div className="story-bridge"><i /> OrgMemory reads the surrounding evidence</div>
              <div className="story-block true">
                <span>What actually changed</span>
                <strong>Checkout moved from the legacy payments endpoint to V2 — in staging only.</strong>
                <p>Production is still on V1. The migration approval and the service owner are linked to this memory.</p>
              </div>
              <footer>
                <span>5 source revisions</span>
                <span>2 decisions</span>
                <span>1 unresolved action</span>
              </footer>
            </div>
          </div>
        </div>
      </section>

      <section className="home-section" id="loop">
        <div className="home-wrap">
          <div className="reveal">
            <span className="home-eyebrow"><i /> From question to remembered outcome</span>
            <h2 className="home-h2">Not another search box.<br />An assistant that closes the loop.</h2>
          </div>

          <div className="loop-grid">
            {loopSteps.map(([title, copy], index) => (
              <article className="loop-step reveal" style={{ ["--i" as string]: index } as CSSProperties} key={title}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <h3>{title}</h3>
                <p>{copy}</p>
              </article>
            ))}
          </div>

          <div className="channel-demo reveal">
            <div className="channel-msg">
              <span>SL</span>
              <div>
                <b>#incident-checkout</b>
                <p>
                  <span className="tag">@orgmemory</span> checkout is failing. Find out why and
                  prepare a fix.
                </p>
              </div>
            </div>
            <div className="channel-thread" aria-hidden="true" />
            <div className="channel-msg">
              <span className="org"><RunbookMark /></span>
              <div>
                <b>OrgMemory · answered in thread</b>
                <p>
                  Production still points at the retired payments endpoint. I have prepared a scoped
                  config change and linked the three sources I used.{" "}
                  <strong>Waiting on approval from the service owner.</strong>
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="home-final">
        <div className="home-wrap">
          <span className="final-mark" aria-hidden="true"><i /><i /><i /><RunbookMark /></span>
          <h2>Give everyone the context to understand — and the agency to act.</h2>
          <p>
            Connect your first source in a few minutes. OrgMemory never sends source credentials to
            the browser or to a model.
          </p>
          <div className="final-actions">
            <Link className="home-btn" href="/login">Build your company brain</Link>
            <Link className="home-btn quiet" href="/docs">Read the docs</Link>
          </div>
          <div className="final-auth">
            <span>Sign in with Google</span>
            <span>· GitHub</span>
            <span>· or a work email code</span>
          </div>
        </div>
      </section>

      <footer className="home-footer">
        <div>
          <div>
            <RunbookLogo />
            <p>The source-backed operating brain for your company.</p>
          </div>
          <nav>
            <span>Product</span>
            <Link href="#connect">Connect sources</Link>
            <Link href="#swarm">Subagent swarm</Link>
            <Link href="#loop">How it works</Link>
          </nav>
          <nav>
            <span>Developers</span>
            <Link href="/docs">Documentation</Link>
            <Link href="/docs#python-sdk">Python SDK</Link>
            <Link href="/docs#mcp">MCP</Link>
          </nav>
          <nav>
            <span>Trust</span>
            <Link href="/docs#security">Security</Link>
            <Link href="/docs#envelopes">Context envelopes</Link>
            <Link href="/login">Open workspace</Link>
          </nav>
        </div>
      </footer>
    </main>
  );
}
