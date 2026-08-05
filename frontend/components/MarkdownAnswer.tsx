import { Fragment, type ReactNode } from "react";

function inlineMarkdown(value: string): ReactNode[] {
  const tokens = value.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
  return tokens.filter(Boolean).map((token, index) => {
    if (token.startsWith("**") && token.endsWith("**")) return <strong key={index}>{token.slice(2, -2)}</strong>;
    if (token.startsWith("`") && token.endsWith("`")) return <code key={index}>{token.slice(1, -1)}</code>;
    if (token.startsWith("*") && token.endsWith("*")) return <em key={index}>{token.slice(1, -1)}</em>;
    return <Fragment key={index}>{token}</Fragment>;
  });
}

export default function MarkdownAnswer({children}:{children:string}) {
  const blocks: ReactNode[] = [];
  const lines = children.replace(/\r\n/g, "\n").split("\n");
  let list: string[] = [];
  function flushList() {
    if (!list.length) return;
    blocks.push(<ul key={`list-${blocks.length}`}>{list.map((item, index) => <li key={index}>{inlineMarkdown(item)}</li>)}</ul>);
    list = [];
  }
  lines.forEach((raw, index) => {
    const line = raw.trim();
    if (!line) { flushList(); return; }
    if (line.startsWith("- ")) { list.push(line.slice(2)); return; }
    flushList();
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) blocks.push(<h3 key={index}>{inlineMarkdown(heading[2])}</h3>);
    else if (/^\*\*[^*]+\*\*$/.test(line)) blocks.push(<h3 key={index}>{line.slice(2, -2)}</h3>);
    else blocks.push(<p key={index}>{inlineMarkdown(line)}</p>);
  });
  flushList();
  return <div className="markdown-answer">{blocks}</div>;
}
