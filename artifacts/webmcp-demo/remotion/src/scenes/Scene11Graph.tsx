import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene11Graph: React.FC = () => (
  <ScreenshotScene
    image="15-graph.png"
    eyebrow="Application flow • relate"
    title="The graph preserves provenance and relationships"
    detail="Sources, revisions, memories, entities, services, contradictions, ownership, and dependencies stay connected."
    timeRange="02:10 — 02:22"
    chapter={11}
    focusX={0.56}
    focusY={0.67}
    callouts={[
      {
        x: 650,
        y: 515,
        width: 690,
        height: 470,
        label: "evidence graph • traversable relationships",
        enterAt: 1.4,
      },
    ]}
  />
);
