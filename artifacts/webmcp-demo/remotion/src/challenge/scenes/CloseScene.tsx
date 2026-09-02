import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptureBackground, SceneShell } from "../SceneChrome";

export const CloseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const title = spring({
    frame: frame - 8,
    fps,
    config: { damping: 22, stiffness: 105, mass: 0.9 },
    durationInFrames: 34,
  });
  return (
    <SceneShell>
      <CaptureBackground image="11-governed-tools.png" brightness={0.22} blur={5} toScale={1.06} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 44%, rgba(24,76,60,0.34), rgba(2,8,7,0.91) 67%)",
        }}
      />
      <Interactive.Div
        name="Closing title"
        style={{
          position: "absolute",
          left: 170,
          right: 170,
          top: 178,
          textAlign: "center",
          color: "#f6fffb",
          opacity: title,
          translate: interpolate(title, [0, 1], ["0px 20px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div
          style={{
            color: "#9df4d3",
            fontSize: 18,
            fontWeight: 840,
            letterSpacing: "0.17em",
            textTransform: "uppercase",
          }}
        >
          21 browser-native tools
        </div>
        <div
          style={{
            marginTop: 24,
            fontSize: 78,
            lineHeight: 0.98,
            fontWeight: 790,
            letterSpacing: "-0.055em",
          }}
        >
          Brief before action.
          <br />
          Report the outcome.
        </div>
        <div
          style={{
            marginTop: 34,
            color: "rgba(231,248,241,0.70)",
            fontSize: 29,
            lineHeight: 1.32,
          }}
        >
          The authenticated page is the memory surface. The organization keeps the learning.
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Brand lockup"
        style={{
          position: "absolute",
          left: 610,
          right: 610,
          bottom: 142,
          padding: "28px 32px",
          borderRadius: 22,
          backgroundColor: "rgba(3,13,10,0.84)",
          border: "1px solid rgba(157,244,211,0.26)",
          boxShadow: "0 28px 88px rgba(0,0,0,0.40)",
          textAlign: "center",
          opacity: interpolate(frame, [2.8 * fps, 4.0 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ color: "#9df4d3", fontSize: 25, fontWeight: 820 }}>OrgMemory</div>
        <div
          style={{
            marginTop: 8,
            color: "white",
            fontSize: 30,
            fontWeight: 720,
            letterSpacing: "-0.025em",
          }}
        >
          Your organization remembers.
        </div>
      </Interactive.Div>
    </SceneShell>
  );
};
