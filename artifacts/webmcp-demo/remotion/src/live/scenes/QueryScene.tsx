import { useCurrentFrame, useVideoConfig } from "remotion";
import { FastForward, LiveScene } from "../LiveChrome";

const QUERY = "What is blocking the checkout OAuth launch, and what should we do next?";

export const QueryScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const visible = Math.floor(Math.min(1, frame / (6 * fps)) * QUERY.length);
  const waiting = frame > 10 * fps;
  return (
    <LiveScene
      image={waiting ? "04-query-tools.png" : "02-query-typed.png"}
      route="/webmcp"
      kicker="Real query"
      title="Ask the workspace what is blocking launch."
      body={`${QUERY.slice(0, visible)}${visible < QUERY.length ? "▋" : ""}`}
      highlights={[{ x: 295, y: 528, width: 985, height: 58, label: "TYPED INTO PRODUCTION" }]}
    >
      {frame > 11 * fps ? <FastForward /> : null}
    </LiveScene>
  );
};
