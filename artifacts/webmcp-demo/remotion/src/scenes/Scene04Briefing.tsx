import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene04Briefing: React.FC = () => (
  <ScreenshotScene
    image="03-real-tool-discovery.png"
    eyebrow="Pre-action briefing"
    title="Brief before changing production"
    detail="One task-specific call returns the applicable memories and a human-approval verdict."
    timeRange="00:36 — 00:54"
    chapter={4}
    focusX={0.91}
    focusY={0.44}
    command={'get_orgmemory_briefing({service: "payments"})'}
    callouts={[
      {
        x: 1518,
        y: 372,
        width: 360,
        height: 133,
        label: "6 memories • approval required",
        enterAt: 1.2,
      },
      {
        x: 1518,
        y: 516,
        width: 360,
        height: 390,
        label: "incidents • dependencies • decisions",
        enterAt: 5.2,
      },
    ]}
    metrics={[
      { value: "6", label: "memories" },
      { value: "113ms", label: "briefing" },
    ]}
  />
);
