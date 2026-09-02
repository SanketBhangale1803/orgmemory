import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { FINAL_COLORS } from "../constants";
import { FinalCapture, FinalSceneShell, ToolNameChip } from "../FinalChrome";

export const FinalCloseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const title = spring({
    frame: frame - 8,
    fps,
    durationInFrames: 36,
    config: { damping: 22, stiffness: 104, mass: 0.9 },
  });
  const links = spring({
    frame: frame - 4.8 * fps,
    fps,
    durationInFrames: 34,
    config: { damping: 21, stiffness: 108, mass: 0.86 },
  });

  return (
    <FinalSceneShell route="/webmcp" label="WebMCP Challenge 2026" dark>
      <FinalCapture image="01-command-center.png" brightness={0.20} blur={5} toScale={1.055} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 43%, rgba(24,76,60,0.35), rgba(2,8,7,0.92) 68%)",
        }}
      />

      <Interactive.Div
        name="Closing promise"
        style={{
          position: "absolute",
          left: 175,
          right: 175,
          top: 152,
          textAlign: "center",
          color: "#f6fffb",
          opacity: title,
          translate: interpolate(title, [0, 1], ["0px 22px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div style={{ color: FINAL_COLORS.mint, fontSize: 19, fontWeight: 850, letterSpacing: "0.17em", textTransform: "uppercase" }}>
          OrgMemory
        </div>
        <div style={{ marginTop: 23, fontSize: 76, lineHeight: 0.99, fontWeight: 795, letterSpacing: "-0.055em" }}>
          Put what your organization
          <br />
          has learned to work.
        </div>
        <div style={{ marginTop: 29, color: "rgba(231,248,241,0.72)", fontSize: 28, lineHeight: 1.35 }}>
          Full company context — with evidence, permissions, and human control.
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Key WebMCP calls"
        style={{
          position: "absolute",
          left: "50%",
          top: 606,
          display: "flex",
          alignItems: "center",
          gap: 15,
          translate: "-50% 0px",
          opacity: interpolate(frame, [2.4 * fps, 3.6 * fps], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <ToolNameChip name="get_orgmemory_briefing" />
        <span style={{ color: "rgba(231,248,241,0.48)", fontSize: 28 }}>→</span>
        <ToolNameChip name="record_orgmemory_outcome" />
      </Interactive.Div>

      <Interactive.Div
        name="Submission links"
        style={{
          position: "absolute",
          left: 445,
          right: 445,
          bottom: 112,
          padding: "24px 28px",
          borderRadius: 22,
          backgroundColor: "rgba(3,13,10,0.88)",
          border: "1px solid rgba(157,244,211,0.28)",
          boxShadow: "0 28px 90px rgba(0,0,0,0.42)",
          textAlign: "center",
          opacity: links,
          scale: interpolate(links, [0, 1], [0.97, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ color: FINAL_COLORS.mint, fontSize: 25, fontWeight: 840 }}>orgmemory.vercel.app</div>
        <div style={{ marginTop: 10, color: "rgba(238,252,246,0.76)", fontFamily: "SFMono-Regular, Menlo, Consolas, monospace", fontSize: 19 }}>
          github.com/SanketBhangale1803/orgmemory
        </div>
        <div style={{ marginTop: 13, color: "white", fontSize: 20, fontWeight: 760, letterSpacing: "0.12em" }}>
          WEBMCP CHALLENGE 2026
        </div>
      </Interactive.Div>
    </FinalSceneShell>
  );
};
