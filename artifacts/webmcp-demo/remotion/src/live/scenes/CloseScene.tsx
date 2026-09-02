import { LiveScene } from "../LiveChrome";

export const CloseScene: React.FC = () => (
  <LiveScene
    image="11-workspace.png"
    route="/workspace"
    kicker="OrgMemory"
    title="Full company context. Evidence. Human control."
    body="People and browser agents check what matters before they act — and report what happened afterward."
    dark
  />
);
