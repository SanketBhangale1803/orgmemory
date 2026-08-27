import type { Metadata } from "next";
import WebMCPDemo from "@/components/WebMCPDemo";

export const metadata: Metadata = {
  title: "WebMCP — OrgMemory",
  description:
    "OrgMemory gives browser AI agents organizational memory: they discover the page tools, search what happened before, combine it with live context, and answer with evidence.",
};

export default function WebMCPPage() {
  return <WebMCPDemo />;
}
