import { LiveScene } from "../LiveChrome";

export const GateScene: React.FC = () => (
  <LiveScene
    image="09-reconcile-result.png"
    route="/webmcp"
    kicker="Permission boundary"
    title="Proposed — and stopped."
    body="The agent found the conflict and proposed one correction. Approval is required. Nothing was applied."
    highlights={[
      { x: 296, y: 433, width: 984, height: 251, label: "APPROVAL REQUIRED" },
      { x: 296, y: 694, width: 984, height: 214, label: "NOTHING APPLIED" },
    ]}
  />
);
