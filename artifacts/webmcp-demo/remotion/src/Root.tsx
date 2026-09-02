import { Composition } from "remotion";
import { OrgMemoryDemo } from "./Composition";
import { OrgMemoryChallengeSlow } from "./challenge/ChallengeComposition";
import { TOTAL_FRAMES } from "./challenge/constants";
import { OrgMemoryLiveWebMCP } from "./live/LiveComposition";
import { LIVE_TOTAL_FRAMES } from "./live/constants";
import { OrgMemoryWebMCPFinal } from "./final/FinalComposition";
import { FINAL_TOTAL_FRAMES } from "./final/constants";
import "./fonts";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="OrgMemoryWebMCPFinal"
        component={OrgMemoryWebMCPFinal}
        durationInFrames={FINAL_TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="OrgMemoryLiveWebMCP"
        component={OrgMemoryLiveWebMCP}
        durationInFrames={LIVE_TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="OrgMemoryWebMCPChallengeSlow"
        component={OrgMemoryChallengeSlow}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="OrgMemoryWebMCP"
        component={OrgMemoryDemo}
        durationInFrames={5400}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
