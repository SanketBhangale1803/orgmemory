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
import { FinalCapture, FinalSceneShell } from "../FinalChrome";

const metrics = [
  ["21", "tools exposed"],
  ["14", "read-only"],
  ["6", "human-governed"],
];

export const FinalSurfaceScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <FinalSceneShell route="/webmcp" label="Authenticated WebMCP" dark>
      <FinalCapture image="01-command-center.png" brightness={0.37} blur={2} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 52% 50%, rgba(23,79,60,0.25), rgba(2,8,7,0.83) 72%)",
        }}
      />

      <Interactive.Div
        name="Session boundary"
        style={{
          position: "absolute",
          left: 150,
          top: 188,
          width: 1010,
          opacity: interpolate(frame, [0, 24], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div style={{ color: FINAL_COLORS.mint, fontSize: 18, fontWeight: 840, letterSpacing: "0.16em" }}>
          SIGNED-IN SESSION • PERMISSION-TRIMMED
        </div>
        <div
          style={{
            marginTop: 20,
            fontSize: 82,
            lineHeight: 0.98,
            fontWeight: 790,
            letterSpacing: "-0.055em",
          }}
        >
          Browser-native tools. No separate credential.
        </div>
        <div style={{ marginTop: 26, width: 870, color: "rgba(231,248,241,0.72)", fontSize: 29, lineHeight: 1.35 }}>
          The page exposes only what this authenticated user is already allowed to access.
        </div>
      </Interactive.Div>

      <div
        style={{
          position: "absolute",
          left: 1220,
          top: 175,
          width: 520,
          display: "grid",
          gap: 14,
        }}
      >
        {metrics.map(([value, label], index) => {
          const progress = spring({
            frame: frame - (4.3 + index * 1.15) * fps,
            fps,
            durationInFrames: 30,
            config: { damping: 20, stiffness: 108, mass: 0.84 },
          });
          return (
            <Interactive.Div
              key={label}
              name={`${value} ${label}`}
              style={{
                minHeight: 155,
                display: "grid",
                gridTemplateColumns: "145px 1fr",
                alignItems: "center",
                padding: "24px 30px",
                borderRadius: 22,
                backgroundColor: "rgba(3,13,10,0.92)",
                border: "1px solid rgba(157,244,211,0.24)",
                boxShadow: "0 28px 80px rgba(0,0,0,0.36)",
                opacity: progress,
                translate: interpolate(progress, [0, 1], ["24px 0px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <strong style={{ fontSize: 74, lineHeight: 0.9, letterSpacing: "-0.06em" }}>{value}</strong>
              <span style={{ color: FINAL_COLORS.mint, fontSize: 21, fontWeight: 820, letterSpacing: "0.1em", textTransform: "uppercase" }}>
                {label}
              </span>
            </Interactive.Div>
          );
        })}
      </div>

      <Interactive.Div
        name="Session proof"
        style={{
          position: "absolute",
          left: 150,
          bottom: 148,
          display: "inline-flex",
          alignItems: "center",
          gap: 13,
          padding: "14px 18px",
          borderRadius: 14,
          backgroundColor: "rgba(157,244,211,0.09)",
          border: "1px solid rgba(157,244,211,0.28)",
          color: "#effff9",
          fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
          fontSize: 19,
        }}
      >
        <span style={{ color: FINAL_COLORS.mint }}>✓</span>
        document.modelContext.registerTool(…)
      </Interactive.Div>
    </FinalSceneShell>
  );
};
