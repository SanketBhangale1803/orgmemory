import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene09Memories: React.FC = () => (
  <ScreenshotScene
    image="13-memories.png"
    eyebrow="Application flow • remember"
    title="Extraction produces atomic memories"
    detail="Incidents, procedures, dependencies, and decisions remain typed, scoped, confidence-ranked, and current."
    timeRange="01:46 — 01:58"
    chapter={9}
    focusX={0.56}
    focusY={0.58}
    callouts={[
      {
        x: 270,
        y: 390,
        width: 1390,
        height: 500,
        label: "one claim per governed memory record",
        enterAt: 1.3,
      },
    ]}
  />
);
