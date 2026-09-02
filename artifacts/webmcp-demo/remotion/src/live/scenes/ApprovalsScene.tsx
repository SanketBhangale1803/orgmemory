import { LiveScene } from "../LiveChrome";

export const ApprovalsScene: React.FC = () => (
  <LiveScene
    image="10-approvals-page.png"
    route="/approvals"
    kicker="Human review"
    title="Capability is not authorization."
    body="Repository refreshes, connector writes, and runbook actions keep separate, explicit approval boundaries."
    highlights={[
      { x: 290, y: 220, width: 1340, height: 210, label: "REPOSITORY REQUESTS" },
      { x: 290, y: 465, width: 1340, height: 210, label: "EXTERNAL WRITES" },
    ]}
  />
);
