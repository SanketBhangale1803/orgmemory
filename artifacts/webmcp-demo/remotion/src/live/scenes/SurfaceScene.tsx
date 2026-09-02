import { LiveScene } from "../LiveChrome";

export const SurfaceScene: React.FC = () => (
  <LiveScene
    image="11-workspace.png"
    route="/workspace"
    kicker="Authenticated WebMCP"
    title="37 tools. One existing session."
    body="27 read-only · 9 human-governed. The browser agent receives capability, never a separate credential."
    highlights={[{ x: 1480, y: 76, width: 410, height: 935, label: "LIVE TOOL MANIFEST" }]}
  />
);
