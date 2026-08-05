"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import RunbookLogo from "@/components/RunbookLogo";

export default function HomeNav() {
  const [stuck, setStuck] = useState(false);

  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header className={`home-nav ${stuck ? "stuck" : ""}`}>
      <div>
        <Link href="/" aria-label="OrgMemory home"><RunbookLogo /></Link>
        <nav aria-label="Product">
          <Link href="#connect">Connect</Link>
          <Link href="#swarm">Subagents</Link>
          <Link href="#loop">How it works</Link>
          <Link href="/docs">Docs</Link>
        </nav>
        <div className="home-nav-right">
          <Link href="/login">Log in</Link>
          <Link className="home-btn" href="/login">Start free</Link>
        </div>
      </div>
    </header>
  );
}
