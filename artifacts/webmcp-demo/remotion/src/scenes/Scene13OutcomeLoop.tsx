import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene13OutcomeLoop: React.FC = () => (
  <ScreenshotScene
    image="18-outcome-loop.png"
    eyebrow="Application flow • measure"
    title="The Outcome Loop records what happened next"
    detail="Every served briefing opens a ledger row. Reporting the action and result closes it without changing memory."
    timeRange="02:34 — 02:50"
    chapter={13}
    focusX={0.56}
    focusY={0.6}
    callouts={[
      {
        x: 390,
        y: 602,
        width: 1135,
        height: 135,
        label: "this demo briefing • action not reported • still open",
        enterAt: 2.0,
      },
    ]}
    metrics={[
      { value: "57", label: "served" },
      { value: "7%", label: "closed" },
      { value: "50%", label: "success" },
    ]}
  />
);
