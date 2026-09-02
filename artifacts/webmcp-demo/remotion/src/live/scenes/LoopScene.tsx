import { LiveScene } from "../LiveChrome";

export const LoopScene: React.FC = () => (
  <LiveScene
    image="15-outcome-loop.png"
    route="/loop"
    kicker="Outcome ledger"
    title="Context served. Action taken. Outcome observed."
    body="get_orgmemory_briefing opens a row. record_orgmemory_outcome closes it. Neither operation changes company memory."
    highlights={[{ x: 300, y: 320, width: 1320, height: 235, label: "THE COMPOUNDING LOOP" }]}
  />
);
