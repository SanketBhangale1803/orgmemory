import {
  AbsoluteFill,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptureBackground, SceneLabel, SceneShell } from "../SceneChrome";

const steps = ["CONTEXT SERVED", "ACTION TAKEN", "OUTCOME OBSERVED"];

export const LoopScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const highlight = spring({
    frame: frame - 12 * fps,
    fps,
    config: { damping: 20, stiffness: 105, mass: 0.86 },
    durationInFrames: 34,
  });

  return (
    <SceneShell backgroundColor="#fbf7f5">
      <CaptureBackground image="20-outcome-closed.png" brightness={0.76} fromScale={1.0} toScale={1.03} />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(251,247,245,0.88) 0%, rgba(251,247,245,0.18) 40%, rgba(251,247,245,0.15) 100%)",
        }}
      />
      <SceneLabel index="05" label="The outcome loop" />

      <Interactive.Div
        name="Loop headline"
        style={{
          position: "absolute",
          left: 156,
          top: 142,
          width: 1320,
          padding: "24px 28px",
          borderRadius: 22,
          backgroundColor: "rgba(255,255,255,0.95)",
          border: "1px solid rgba(125,23,48,0.15)",
          boxShadow: "0 24px 72px rgba(65,18,28,0.12)",
        }}
      >
        <div
          style={{
            color: "#7d1730",
            fontSize: 55,
            lineHeight: 1.02,
            fontWeight: 790,
            letterSpacing: "-0.05em",
          }}
        >
          Which context actually produced correct action here?
        </div>
      </Interactive.Div>

      <div
        style={{
          position: "absolute",
          left: 228,
          right: 228,
          top: 508,
          display: "grid",
          gridTemplateColumns: "1fr auto 1fr auto 1fr",
          alignItems: "center",
          gap: 18,
        }}
      >
        {steps.map((step, index) => {
          const progress = spring({
            frame: frame - (5 + index * 2.0) * fps,
            fps,
            config: { damping: 18, stiffness: 120, mass: 0.8 },
            durationInFrames: 30,
          });
          return (
            <div key={step} style={{ display: "contents" }}>
              <Interactive.Div
                name={step}
                style={{
                  minHeight: 132,
                  display: "grid",
                  placeItems: "center",
                  padding: "20px",
                  borderRadius: 20,
                  backgroundColor: index === 2 ? "#174f3c" : "rgba(255,255,255,0.95)",
                  border: index === 2
                    ? "1px solid rgba(23,79,60,0.36)"
                    : "1px solid rgba(125,23,48,0.16)",
                  boxShadow: "0 22px 62px rgba(52,14,22,0.11)",
                  color: index === 2 ? "#effff9" : "#5b1224",
                  fontSize: 21,
                  fontWeight: 840,
                  letterSpacing: "0.1em",
                  textAlign: "center",
                  opacity: progress,
                  scale: interpolate(progress, [0, 1], [0.96, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                {step}
              </Interactive.Div>
              {index < steps.length - 1 ? (
                <div style={{ color: "#7d1730", fontSize: 38, fontWeight: 850 }}>→</div>
              ) : null}
            </div>
          );
        })}
      </div>

      <Interactive.Div
        name="Closed outcome highlight"
        style={{
          position: "absolute",
          left: 390,
          top: 274,
          width: 1140,
          height: 144,
          borderRadius: 20,
          border: "3px solid #174f3c",
          backgroundColor: "rgba(23,79,60,0.035)",
          boxShadow: "0 0 0 10px rgba(23,79,60,0.06), 0 26px 80px rgba(52,14,22,0.12)",
          opacity: highlight,
          scale: interpolate(highlight, [0, 1], [0.985, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 18,
            top: 16,
            padding: "10px 13px",
            borderRadius: 10,
            backgroundColor: "#174f3c",
            color: "#f0fff9",
            fontSize: 17,
            fontWeight: 800,
            letterSpacing: "0.08em",
          }}
        >
          CLOSED • SUCCEEDED • REWARD +1
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Compounding note"
        style={{
          position: "absolute",
          left: 410,
          bottom: 145,
          width: 1100,
          padding: "19px 24px",
          borderRadius: 18,
          backgroundColor: "#7d1730",
          color: "#fff9fb",
          boxShadow: "0 22px 70px rgba(89,13,32,0.20)",
          fontSize: 28,
          lineHeight: 1.28,
          fontWeight: 720,
          textAlign: "center",
        }}
      >
        The one asset a better model cannot copy — and it compounds with every run.
      </Interactive.Div>
    </SceneShell>
  );
};
