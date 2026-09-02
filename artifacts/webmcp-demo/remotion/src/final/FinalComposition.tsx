import { Audio } from "@remotion/media";
import { AbsoluteFill, interpolate, Sequence, staticFile } from "remotion";
import { FinalCaptions } from "./FinalCaptions";
import { FinalPointer } from "./FinalPointer";
import { FINAL_SCENES, FINAL_TOTAL_FRAMES } from "./constants";
import { FinalApprovalsScene } from "./scenes/ApprovalsScene";
import { FinalBoundaryScene } from "./scenes/BoundaryScene";
import { FinalBriefingScene } from "./scenes/BriefingScene";
import { FinalCloseScene } from "./scenes/CloseScene";
import { FinalIntroScene } from "./scenes/IntroScene";
import { FinalLoopScene } from "./scenes/LoopScene";
import { FinalSurfaceScene } from "./scenes/SurfaceScene";

export const OrgMemoryWebMCPFinal: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#06100e" }}>
    <Sequence from={FINAL_SCENES.intro.from} durationInFrames={FINAL_SCENES.intro.duration} premountFor={30}>
      <FinalIntroScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.surface.from} durationInFrames={FINAL_SCENES.surface.duration} premountFor={30}>
      <FinalSurfaceScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.briefing.from} durationInFrames={FINAL_SCENES.briefing.duration} premountFor={30}>
      <FinalBriefingScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.boundary.from} durationInFrames={FINAL_SCENES.boundary.duration} premountFor={30}>
      <FinalBoundaryScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.approvals.from} durationInFrames={FINAL_SCENES.approvals.duration} premountFor={30}>
      <FinalApprovalsScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.loop.from} durationInFrames={FINAL_SCENES.loop.duration} premountFor={30}>
      <FinalLoopScene />
    </Sequence>
    <Sequence from={FINAL_SCENES.close.from} durationInFrames={FINAL_SCENES.close.duration} premountFor={30}>
      <FinalCloseScene />
    </Sequence>

    <Sequence from={18} durationInFrames={FINAL_TOTAL_FRAMES - 18} premountFor={18}>
      <Audio src={staticFile("audio/narration-final.mp3")} volume={1} />
    </Sequence>
    <Audio
      src={staticFile("audio/ambient.wav")}
      loop
      durationInFrames={FINAL_TOTAL_FRAMES}
      volume={(frame) =>
        interpolate(frame, [0, 60, FINAL_TOTAL_FRAMES - 150, FINAL_TOTAL_FRAMES - 1], [0, 0.075, 0.075, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      }
    />
    <FinalPointer />
    <FinalCaptions />
  </AbsoluteFill>
);
