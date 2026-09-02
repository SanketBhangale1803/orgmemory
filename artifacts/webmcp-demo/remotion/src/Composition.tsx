import { Audio } from "@remotion/media";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { AbsoluteFill, interpolate, staticFile } from "remotion";
import { AnimatedCaptions } from "./components/AnimatedCaptions";
import { GlobalProgress } from "./components/GlobalProgress";
import { Scene01WebMcpSurface } from "./scenes/Scene01WebMcpSurface";
import { Scene02Workspace } from "./scenes/Scene02Workspace";
import { Scene03ToolDiscovery } from "./scenes/Scene03ToolDiscovery";
import { Scene04Briefing } from "./scenes/Scene04Briefing";
import { Scene05Investigation } from "./scenes/Scene05Investigation";
import { Scene06Approval } from "./scenes/Scene06Approval";
import { Scene07FreshAgent } from "./scenes/Scene07FreshAgent";
import { Scene08Ingest } from "./scenes/Scene08Ingest";
import { Scene09Memories } from "./scenes/Scene09Memories";
import { Scene10Profiles } from "./scenes/Scene10Profiles";
import { Scene11Graph } from "./scenes/Scene11Graph";
import { Scene12MemoryWork } from "./scenes/Scene12MemoryWork";
import { Scene13OutcomeLoop } from "./scenes/Scene13OutcomeLoop";
import { Scene14Final } from "./scenes/Scene14Final";

const transitionTiming = linearTiming({ durationInFrames: 18 });

export const OrgMemoryDemo: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#06100e",
        fontFamily: '"OrgMemory Sans", Arial, sans-serif',
      }}
    >
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={378} name="WebMCP surface">
          <Scene01WebMcpSurface />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={318} name="Authenticated workspace">
          <Scene02Workspace />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={438} name="Tool discovery">
          <Scene03ToolDiscovery />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={558} name="Pre-action briefing">
          <Scene04Briefing />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-left" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={438} name="Agent investigation">
          <Scene05Investigation />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={378} name="Human approval">
          <Scene06Approval />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={438} name="Fresh-agent handoff">
          <Scene07FreshAgent />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={378} name="Add Knowledge">
          <Scene08Ingest />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-left" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={378} name="Atomic memories">
          <Scene09Memories />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={378} name="Current profiles">
          <Scene10Profiles />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-right" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={378} name="Memory Graph">
          <Scene11Graph />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={378} name="Memory Work">
          <Scene12MemoryWork />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-left" })}
          timing={transitionTiming}
        />
        <TransitionSeries.Sequence durationInFrames={498} name="Outcome Loop">
          <Scene13OutcomeLoop />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={transitionTiming} />
        <TransitionSeries.Sequence durationInFrames={300} name="Complete loop">
          <Scene14Final />
        </TransitionSeries.Sequence>
      </TransitionSeries>

      <Audio
        src={staticFile("audio/narration-daniel.mp3")}
        durationInFrames={5400}
        volume={1}
      />
      <Audio
        src={staticFile("audio/ambient.wav")}
        durationInFrames={5400}
        volume={(frame) =>
          interpolate(frame, [0, 60, 5220, 5399], [0, 0.55, 0.55, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })
        }
      />
      <AnimatedCaptions />
      <GlobalProgress />
    </AbsoluteFill>
  );
};
