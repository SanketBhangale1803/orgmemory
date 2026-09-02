import { LiveScene } from "../LiveChrome";

export const IntroScene: React.FC = () => (
  <LiveScene
    image="00-landing.png"
    route="/"
    kicker="The problem"
    title="Context should arrive before the change."
    body="Incidents, decisions, dependencies, owners, and runbooks — tied back to evidence."
  />
);
