import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene01WebMcpSurface: React.FC = () => (
  <ScreenshotScene
    image="01-command-center.png"
    eyebrow="Browser-native capability"
    title="WebMCP surface"
    detail="The page exposes organizational memory to a browser agent inside the signed-in workspace."
    timeRange="00:00 — 00:12"
    chapter={1}
    focusX={0.62}
    focusY={0.58}
    callouts={[
      {
        x: 1088,
        y: 652,
        width: 370,
        height: 176,
        label: "permission-annotated tool surface",
        enterAt: 2.2,
      },
    ]}
    metrics={[
      { value: "21", label: "tools" },
      { value: "14", label: "read only" },
      { value: "6", label: "governed" },
    ]}
  />
);
