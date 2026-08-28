"use client";

import Link from "next/link";
import CommandMenu, { useCommandMenu } from "@/components/CommandMenu";
import { RunbookMark } from "@/components/RunbookLogo";

/* The slim counterpart to the chat's own header, for the pages the chat sends
   people to. Anything reached from the chat should feel like the chat, not like
   a second product with its own navigation model — so this bar carries no menu
   of its own, only the same ⌘K that works everywhere else. */
export default function ChatBackBar({ user, title }: { user?: any; title: string }) {
  const command = useCommandMenu();
  const isAdmin = user?.role === "owner" || user?.role === "admin";
  const initials = (user?.display_name || user?.email || "OM")
    .split(/\s+/)
    .map((part: string) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <>
      <header className="ws-bar">
        <Link href="/workspace" className="ws-id" aria-label="Back to chat">
          <RunbookMark />
          <span>
            <strong>OrgMemory</strong>
            <small>{title}</small>
          </span>
        </Link>
        <div className="ws-controls">
          <button
            type="button"
            className="ws-pill ws-jump"
            onClick={() => command.setOpen(true)}
            title="Jump anywhere, or ask a question"
          >
            <span>Jump to…</span>
            <kbd>⌘K</kbd>
          </button>
          <Link className="ws-pill quiet" href="/workspace">
            <span>← Back to chat</span>
          </Link>
          <Link className="ws-avatar" href="/account" title="Account and workspace">
            {initials}
          </Link>
        </div>
      </header>
      <CommandMenu open={command.open} onClose={command.close} isAdmin={isAdmin} />
    </>
  );
}
