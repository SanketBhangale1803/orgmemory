import Link from "next/link";
import RunbookLogo from "@/components/RunbookLogo";

export default function PublicNav({ compact = false }: { compact?: boolean }) {
  return (
    <header className={`om-nav ${compact ? "compact" : ""}`}>
      <Link href="/" aria-label="OrgMemory home">
        <RunbookLogo inverted />
      </Link>
      <nav aria-label="Public navigation">
        <Link href="/#sources">Sources</Link>
        <Link href="/#swarm">Swarm</Link>
        <Link href="/#workflow">Workflow</Link>
        <Link href="/#developers">Developers</Link>
        <Link href="/docs">Docs</Link>
      </nav>
      <div className="om-nav-actions">
        <Link className="om-nav-login" href="/login">Log in</Link>
        <Link className="om-button small" href="/login">
          Build your brain <span>↗</span>
        </Link>
      </div>
    </header>
  );
}
