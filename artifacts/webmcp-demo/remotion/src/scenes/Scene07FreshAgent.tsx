import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene07FreshAgent: React.FC = () => (
  <ScreenshotScene
    image="09-fresh-agent-bridge.png"
    eyebrow="Session 2"
    title="A fresh agent retrieves the approved memory"
    detail="There is no shared chat and no carried prompt context. The durable procedure is retrieved again."
    timeRange="01:20 — 01:34"
    chapter={7}
    focusX={0.65}
    focusY={0.67}
    callouts={[
      {
        x: 480,
        y: 594,
        width: 1310,
        height: 320,
        label: "new session • same authorized company memory",
        enterAt: 1.5,
      },
    ]}
  />
);
