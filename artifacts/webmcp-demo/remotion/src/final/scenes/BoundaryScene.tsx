import {
  AbsoluteFill,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { FINAL_COLORS } from "../constants";
import { FinalCapture, FinalSceneShell, ToolNameChip } from "../FinalChrome";

const ResultCard: React.FC<{ index: string; progress: number }> = ({ index, progress }) => (
  <Interactive.Div
    name={`Deterministic result ${index}`}
    style={{
      padding: "24px 26px",
      borderRadius: 20,
      backgroundColor: "rgba(4,13,11,0.94)",
      border: "1px solid rgba(157,244,211,0.24)",
      boxShadow: "0 24px 76px rgba(0,0,0,0.34)",
      color: "#f5fffb",
      opacity: progress,
      translate: interpolate(progress, [0, 1], [index === "01" ? "-22px 0px" : "22px 0px", "0px 0px"], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      }),
    }}
  >
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <ToolNameChip name="get_orgmemory_briefing" />
      <span style={{ color: "rgba(229,247,240,0.52)", fontFamily: "SFMono-Regular, Menlo, Consolas, monospace", fontSize: 16 }}>
        RUN {index}
      </span>
    </div>
    <div style={{ marginTop: 20, padding: "15px 17px", borderRadius: 12, backgroundColor: "rgba(255,255,255,0.055)", fontSize: 20 }}>
      Restart the payments connection pool
    </div>
    <div style={{ marginTop: 17, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <strong style={{ color: "#ff9db4", fontSize: 22, letterSpacing: "0.08em" }}>REQUIRES APPROVAL</strong>
      <span style={{ color: FINAL_COLORS.mint, fontFamily: "SFMono-Regular, Menlo, Consolas, monospace", fontSize: 17 }}>
        digest 90d2…71a ✓
      </span>
    </div>
  </Interactive.Div>
);

export const FinalBoundaryScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const first = spring({ frame: frame - 1.2 * fps, fps, durationInFrames: 30, config: { damping: 20, stiffness: 108, mass: 0.86 } });
  const second = spring({ frame: frame - 4.0 * fps, fps, durationInFrames: 30, config: { damping: 20, stiffness: 108, mass: 0.86 } });
  const boundary = spring({ frame: frame - 10.5 * fps, fps, durationInFrames: 34, config: { damping: 21, stiffness: 104, mass: 0.88 } });

  return (
    <FinalSceneShell route="/webmcp" label="Deterministic control" dark>
      <FinalCapture image="01-command-center.png" brightness={0.22} blur={6} />
      <AbsoluteFill style={{ backgroundColor: "rgba(1,7,6,0.70)" }} />

      <Interactive.Div
        name="Determinism headline"
        style={{
          position: "absolute",
          left: 194,
          top: 142,
          right: 194,
          textAlign: "center",
          color: "#f5fffb",
        }}
      >
        <div style={{ color: FINAL_COLORS.mint, fontSize: 17, fontWeight: 850, letterSpacing: "0.15em" }}>SAME MEMORY • SAME INTENT</div>
        <div style={{ marginTop: 15, fontSize: 58, lineHeight: 1.02, fontWeight: 790, letterSpacing: "-0.05em" }}>
          Same verdict. Every time.
        </div>
      </Interactive.Div>

      <div style={{ position: "absolute", left: 170, right: 170, top: 318, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <ResultCard index="01" progress={first} />
        <ResultCard index="02" progress={second} />
      </div>

      <Interactive.Div
        name="Intent boundary comparison"
        style={{
          position: "absolute",
          left: 222,
          right: 222,
          bottom: 142,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 18,
          opacity: boundary,
          translate: interpolate(boundary, [0, 1], ["0px 18px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div style={{ padding: "22px 24px", borderRadius: 20, backgroundColor: "rgba(23,79,60,0.96)", border: "1px solid rgba(157,244,211,0.34)" }}>
          <div style={{ color: "rgba(232,255,246,0.64)", fontSize: 16, fontWeight: 780, letterSpacing: "0.10em" }}>READ-ONLY INVESTIGATION</div>
          <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", gap: 18, alignItems: "center" }}>
            <strong style={{ fontSize: 27 }}>Why is payments failing again?</strong>
            <span style={{ color: FINAL_COLORS.mint, fontSize: 20, fontWeight: 860, letterSpacing: "0.10em" }}>PROCEED</span>
          </div>
        </div>
        <div style={{ padding: "22px 24px", borderRadius: 20, backgroundColor: "rgba(125,23,48,0.96)", border: "1px solid rgba(255,158,181,0.34)" }}>
          <div style={{ color: "rgba(255,236,241,0.64)", fontSize: 16, fontWeight: 780, letterSpacing: "0.10em" }}>PRODUCTION ACTION</div>
          <div style={{ marginTop: 12, display: "flex", justifyContent: "space-between", gap: 18, alignItems: "center" }}>
            <strong style={{ fontSize: 27 }}>Restart the connection pool</strong>
            <span style={{ color: "#ffadc0", fontSize: 20, fontWeight: 860, letterSpacing: "0.08em" }}>HUMAN APPROVAL</span>
          </div>
        </div>
      </Interactive.Div>
    </FinalSceneShell>
  );
};
