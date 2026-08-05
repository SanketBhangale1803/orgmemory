"use client";

import { useState } from "react";

type CodeBlockProps = {
  children: string;
  label?: string;
  language?: string;
};

export default function CodeBlock({
  children,
  label = "Example",
  language = "text",
}: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  async function copyCode() {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  return (
    <div className="docs-code">
      <div className="docs-code__bar">
        <span>
          <i aria-hidden="true" />
          {label}
        </span>
        <button type="button" onClick={copyCode} aria-label={`Copy ${label}`}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code data-language={language}>{children}</code>
      </pre>
    </div>
  );
}
