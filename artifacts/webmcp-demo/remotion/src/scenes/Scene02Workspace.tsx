import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene02Workspace: React.FC = () => (
  <ScreenshotScene
    image="02-workspace-tools.png"
    eyebrow="Authenticated workspace"
    title="The page registers the tools"
    detail="document.modelContext binds schemas and annotations to the user's existing session."
    timeRange="00:12 — 00:22"
    chapter={2}
    focusX={0.48}
    focusY={0.18}
    titleSide="right"
    command="document.modelContext → signed-in OrgMemory session"
    callouts={[
      {
        x: 480,
        y: 10,
        width: 218,
        height: 60,
        label: "WebMCP ready • 21 tools",
        enterAt: 1.4,
      },
    ]}
  />
);
