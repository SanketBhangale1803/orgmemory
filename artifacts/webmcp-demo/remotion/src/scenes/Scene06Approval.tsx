import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene06Approval: React.FC = () => (
  <ScreenshotScene
    image="08-human-approval-gate.png"
    eyebrow="Governed write"
    title="The agent proposes; a person decides"
    detail="Write-capable tools create a reviewable claim. The application states that nothing is saved yet."
    timeRange="01:08 — 01:20"
    chapter={6}
    focusX={0.67}
    focusY={0.53}
    titleSide="left"
    callouts={[
      {
        x: 560,
        y: 300,
        width: 1230,
        height: 360,
        label: "proposal only • explicit approval required",
        enterAt: 1.2,
      },
    ]}
  />
);
