import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene08Ingest: React.FC = () => (
  <ScreenshotScene
    image="12-ingest.png"
    eyebrow="Application flow • ingest"
    title="Add Knowledge preserves the source"
    detail="Documents, repositories, Slack channels, and connected sources enter one governed extraction path."
    timeRange="01:34 — 01:46"
    chapter={8}
    focusX={0.35}
    focusY={0.42}
    titleSide="right"
    callouts={[
      {
        x: 165,
        y: 225,
        width: 530,
        height: 195,
        label: "documents • repositories • Slack",
        enterAt: 1.2,
      },
      {
        x: 165,
        y: 520,
        width: 845,
        height: 420,
        label: "source preserved before extraction",
        enterAt: 4.2,
      },
    ]}
  />
);
