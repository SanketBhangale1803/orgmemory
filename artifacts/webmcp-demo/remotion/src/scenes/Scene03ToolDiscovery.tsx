import { ScreenshotScene } from "../components/ScreenshotScene";

export const Scene03ToolDiscovery: React.FC = () => (
  <ScreenshotScene
    image="03-real-tool-discovery.png"
    eyebrow="Observable invocation"
    title="Real browser tool discovery"
    detail="The activity panel records the page-defined tool, its arguments, result count, and latency."
    timeRange="00:22 — 00:36"
    chapter={3}
    focusX={0.9}
    focusY={0.38}
    command="list_orgmemory_spaces() → 21 authorized spaces"
    callouts={[
      {
        x: 1455,
        y: 14,
        width: 450,
        height: 1038,
        label: "5 observable WebMCP calls",
        enterAt: 1.1,
      },
      {
        x: 1518,
        y: 254,
        width: 360,
        height: 104,
        label: "list_orgmemory_spaces • 4 ms",
        enterAt: 3.5,
      },
    ]}
  />
);
