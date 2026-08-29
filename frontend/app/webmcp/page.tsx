import type { Metadata } from "next";
import AgentOperations from "@/components/AgentOperations";

export const metadata: Metadata = {
  title: "Agent operations — OrgMemory",
  description:
    "Reconstruct a project, trace why a decision was made, find what is blocking a launch, and reconcile a contradiction — as WebMCP tool calls against organizational memory.",
};

export default function WebMCPPage() {
  return <AgentOperations />;
}
