import { Audio } from "@remotion/media";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { LiveCaptions } from "./LiveCaptions";
import { LIVE_SCENES, LIVE_TOTAL_FRAMES } from "./constants";
import { ApprovalsScene } from "./scenes/ApprovalsScene";
import { CloseScene } from "./scenes/CloseScene";
import { GateScene } from "./scenes/GateScene";
import { IntroScene } from "./scenes/IntroScene";
import { LoopScene } from "./scenes/LoopScene";
import { QueryScene } from "./scenes/QueryScene";
import { ReconcileScene } from "./scenes/ReconcileScene";
import { ResultScene } from "./scenes/ResultScene";
import { SurfaceScene } from "./scenes/SurfaceScene";

export const OrgMemoryLiveWebMCP: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#fbf7f5" }}>
    <Sequence from={LIVE_SCENES.intro.from} durationInFrames={LIVE_SCENES.intro.duration}><IntroScene /></Sequence>
    <Sequence from={LIVE_SCENES.surface.from} durationInFrames={LIVE_SCENES.surface.duration}><SurfaceScene /></Sequence>
    <Sequence from={LIVE_SCENES.query.from} durationInFrames={LIVE_SCENES.query.duration}><QueryScene /></Sequence>
    <Sequence from={LIVE_SCENES.result.from} durationInFrames={LIVE_SCENES.result.duration}><ResultScene /></Sequence>
    <Sequence from={LIVE_SCENES.reconcile.from} durationInFrames={LIVE_SCENES.reconcile.duration}><ReconcileScene /></Sequence>
    <Sequence from={LIVE_SCENES.gate.from} durationInFrames={LIVE_SCENES.gate.duration}><GateScene /></Sequence>
    <Sequence from={LIVE_SCENES.approvals.from} durationInFrames={LIVE_SCENES.approvals.duration}><ApprovalsScene /></Sequence>
    <Sequence from={LIVE_SCENES.loop.from} durationInFrames={LIVE_SCENES.loop.duration}><LoopScene /></Sequence>
    <Sequence from={LIVE_SCENES.close.from} durationInFrames={LIVE_SCENES.close.duration}><CloseScene /></Sequence>
    <Audio src={staticFile("audio/live-demo.mp3")} volume={1} />
    <Audio src={staticFile("audio/ambient.wav")} loop durationInFrames={LIVE_TOTAL_FRAMES} volume={0.065} />
    <LiveCaptions />
  </AbsoluteFill>
);
