import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene05Investigation: React.FC = () => (
  <ScreenshotScene
    image="07-session-one-answer.png"
    eyebrow="Session 1"
    title="The first agent explains the blast radius"
    detail="Incident precedent, service context, dependencies, and the prior decision arrive as structured memory."
    timeRange="00:54 — 01:08"
    chapter={5}
    focusX={0.63}
    focusY={0.44}
    callouts={[
      {
        x: 520,
        y: 150,
        width: 1270,
        height: 370,
        label: "source-backed answer from company memory",
        enterAt: 1.4,
      },
    ]}
  />
);
