import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene10Profiles: React.FC = () => (
  <ScreenshotScene
    image="14-profiles.png"
    eyebrow="Application flow • assemble"
    title="Profiles are built from current memory"
    detail="The payments profile combines the active concurrency decision, response procedure, and shared database dependency."
    timeRange="01:58 — 02:10"
    chapter={10}
    focusX={0.54}
    focusY={0.52}
    titleSide="right"
    callouts={[
      {
        x: 230,
        y: 350,
        width: 1320,
        height: 565,
        label: "current authorized view • assembled at request time",
        enterAt: 1.3,
      },
    ]}
  />
);
