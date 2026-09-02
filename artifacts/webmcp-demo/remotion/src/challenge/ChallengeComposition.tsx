import { Audio } from "@remotion/media";
import { AbsoluteFill, interpolate, Sequence, staticFile } from "remotion";
import { ChallengeCaptions } from "./ChallengeCaptions";
import { SCENES, TOTAL_FRAMES } from "./constants";
import { BriefingScene } from "./scenes/BriefingScene";
import { BuiltScene } from "./scenes/BuiltScene";
import { CloseScene } from "./scenes/CloseScene";
import { LoopScene } from "./scenes/LoopScene";
import { PermissionScene } from "./scenes/PermissionScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { LivePointer } from "./LivePointer";

export const OrgMemoryChallengeSlow: React.FC = () => (
  <AbsoluteFill
    style={{
      backgroundColor: "#06100e",
      fontFamily: '"OrgMemory Sans", Arial, sans-serif',
    }}
  >
    <Sequence from={SCENES.problem.from} durationInFrames={SCENES.problem.duration}>
      <ProblemScene />
    </Sequence>
    <Sequence from={SCENES.built.from} durationInFrames={SCENES.built.duration}>
      <BuiltScene />
    </Sequence>
    <Sequence from={SCENES.briefing.from} durationInFrames={SCENES.briefing.duration}>
      <BriefingScene />
    </Sequence>
    <Sequence from={SCENES.permission.from} durationInFrames={SCENES.permission.duration}>
      <PermissionScene />
    </Sequence>
    <Sequence from={SCENES.loop.from} durationInFrames={SCENES.loop.duration}>
      <LoopScene />
    </Sequence>
    <Sequence from={SCENES.close.from} durationInFrames={SCENES.close.duration}>
      <CloseScene />
    </Sequence>

    <Sequence from={30} durationInFrames={TOTAL_FRAMES - 30}>
      <Audio src={staticFile("audio/narration-challenge-slow.mp3")} volume={1} />
    </Sequence>
    <Audio
      src={staticFile("audio/ambient.wav")}
      loop
      durationInFrames={TOTAL_FRAMES}
      volume={(frame) =>
        interpolate(frame, [0, 60, TOTAL_FRAMES - 90, TOTAL_FRAMES - 1], [0, 0.13, 0.13, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      }
    />
    <LivePointer />
    <ChallengeCaptions />
  </AbsoluteFill>
);
