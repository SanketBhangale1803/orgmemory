import { LiveScene } from "../LiveChrome";

export const ResultScene: React.FC = () => (
  <LiveScene
    image="05-query-result.png"
    route="/webmcp"
    kicker="Returned result"
    title="One critical gate, traced end to end."
    body="GLM chose find_orgmemory_blockers. The answer names the blocker, the owners, the downstream launch impact, and two cited memories."
    highlights={[
      { x: 296, y: 92, width: 986, height: 90, label: "REAL TOOL CALL · 2538 MS" },
      { x: 296, y: 189, width: 986, height: 270, label: "CITED ANSWER" },
    ]}
  />
);
