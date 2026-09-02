import { useCurrentFrame, useVideoConfig } from "remotion";
import { FastForward, LiveScene } from "../LiveChrome";

export const ReconcileScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const waiting = frame > 7 * fps;
  return (
    <LiveScene
      image={waiting ? "08-reconcile-tools.png" : "06-reconcile-typed.png"}
      route="/webmcp"
      kicker="Governed request"
      title="Reconcile the contradiction and prepare for launch."
      body="A second real prompt asks the agent to move from reading toward organizational change."
      highlights={[{ x: 294, y: 365, width: 987, height: 58, label: "SECOND QUERY" }]}
    >
      {frame > 9 * fps ? <FastForward label="MODEL + TOOL WAIT SKIPPED" /> : null}
    </LiveScene>
  );
};
