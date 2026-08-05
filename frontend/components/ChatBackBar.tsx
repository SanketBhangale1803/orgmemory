"use client";

import Link from "next/link";
import { RunbookMark } from "@/components/RunbookLogo";

/* The slim counterpart to the chat's own header, for the pages the chat sends
   people to. Anything reached from the chat should feel like the chat, not like
   a second product with its own navigation model. */
export default function ChatBackBar({ user, title }: { user?: any; title: string }) {
  const initials = (user?.display_name || user?.email || "OM")
    .split(/\s+/)
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <header className="ws-bar">
      <Link href="/workspace" className="ws-id" aria-label="Back to chat">
        <RunbookMark />
        <span>
          <strong>OrgMemory</strong>
          <small>{title}</small>
        </span>
      </Link>
      <div className="ws-controls">
        <Link className="ws-pill quiet" href="/workspace">
          <span>← Back to chat</span>
        </Link>
        <Link className="ws-avatar" href="/account" title="Account and workspace">
          {initials}
        </Link>
      </div>
    </header>
  );
}
