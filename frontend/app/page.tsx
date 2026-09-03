import Link from "next/link";
import HomeCommandOrb from "@/components/HomeCommandOrb";
import { RunbookMark } from "@/components/RunbookLogo";
import { ORG_READ_TOOLS, ORG_TOOL_NAMES, ORG_WRITE_TOOLS } from "@/lib/orgTools";

/* The landing page names the vertical in the first two lines.
   "Organizational memory" describes a category and sells to nobody. Engineering
   organizations are who this is actually built for — the nouns throughout the
   product are services, incidents, deploys, owners, and decisions — and saying
   so is what separates a product from a demo of a technique. */

export default function HomePage() {
  return (
    <main className="orgmemory-entry">
      <header className="entry-nav">
        <Link href="/" className="entry-brand" aria-label="OrgMemory home">
          <RunbookMark />
          <span>OrgMemory</span>
        </Link>
        <nav aria-label="Public navigation">
          <Link href="/webmcp">WebMCP</Link>
          <Link href="/docs">Docs</Link>
          <Link href="/login" className="entry-login">Log in</Link>
        </nav>
      </header>

      <section className="entry-hero">
        <div className="entry-signal">
          <i />
          The memory layer for engineering organizations
        </div>
        <h1>Give every engineering change its full company context.</h1>
        <p>
          OrgMemory brings together incidents, decisions, dependencies, owners, and runbooks—with
          evidence—so people and AI agents can check what matters before they act.
        </p>
        <HomeCommandOrb />
        <Link href="/webmcp" className="entry-webmcp-status">
          <span><i /> WebMCP ready</span>
          {/* Counts must match what the authenticated page actually registers
              (ORG_TOOLS — the same source /webmcp reports); the marketing
              catalog is a larger superset and would overstate the live surface. */}
          <small>{ORG_TOOL_NAMES.length} tools · {ORG_READ_TOOLS.length} read-only · {ORG_WRITE_TOOLS.length} human-governed</small>
          <b aria-hidden="true">→</b>
        </Link>
      </section>

      <section className="entry-proof" aria-label="How OrgMemory works">
        <article>
          <span>01 / remember</span>
          <h2>Incidents, decisions, and owners stay tied to evidence.</h2>
          <p>
            Code, postmortems, threads, and docs become one time-aware memory graph. Every
            promoted fact cites a source; anything uncertain stays a searchable chunk.
          </p>
        </article>
        <article>
          <span>02 / brief</span>
          <h2>Agents get briefed before they act, not after.</h2>
          <p>
            An agent about to touch a service asks what this company knows first, and gets back
            the decisions that constrain it, the incidents that started the same way, and the
            blast radius — anywhere on the web, through WebMCP.
          </p>
        </article>
        <article>
          <span>03 / govern</span>
          <h2>Agents investigate. People authorize.</h2>
          <p>
            Reads move at machine speed. Anything that would change company memory enters a
            scoped approval queue and waits for a person. Capability is never authorization.
          </p>
        </article>
        <article>
          <span>04 / compound</span>
          <h2>Every answer is scored by what happened next.</h2>
          <p>
            Context served, action taken, outcome observed. The record of which context actually
            produced correct action is the one asset a better model cannot copy.
          </p>
        </article>
      </section>

      <footer className="entry-footer">
        <span>OrgMemory</span>
        <p>Source-backed memory for every teammate and agent.</p>
        <div><Link href="/docs">Documentation</Link><Link href="/login">Enter workspace</Link></div>
      </footer>
    </main>
  );
}
