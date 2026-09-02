import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene12MemoryWork: React.FC = () => (
  <ScreenshotScene
    image="16-memory-work.png"
    eyebrow="Application flow • activate"
    title="Memory Work prepares the output"
    detail="The user describes an outcome once. OrgMemory activates current evidence and keeps connector actions governed."
    timeRange="02:22 — 02:34"
    chapter={12}
    focusX={0.67}
    focusY={0.55}
    callouts={[
      {
        x: 965,
        y: 300,
        width: 720,
        height: 620,
        label: "activate context → prepare → approve handoff",
        enterAt: 1.4,
      },
    ]}
  />
);
