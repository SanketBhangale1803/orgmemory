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

const sources = ["INCIDENTS", "DECISIONS", "DEPENDENCIES", "RUNBOOKS"];

export const FinalIntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const titleOut = interpolate(frame, [4.8 * fps, 6.3 * fps], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const stripIn = spring({
    frame: frame - 6.2 * fps,
    fps,
    durationInFrames: 34,
    config: { damping: 21, stiffness: 105, mass: 0.88 },
  });

  return (
    <FinalSceneShell route="/" label="The problem">
      <FinalCapture image="00-landing-hero.png" fromScale={1} toScale={1.032} position="center top" />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(251,247,245,0.03), rgba(251,247,245,0.06) 52%, rgba(251,247,245,0.92) 87%, #fbf7f5 100%)",
        }}
      />

      <Interactive.Div
        name="Opening title card"
        style={{
          position: "absolute",
          left: 448,
          top: 270,
          width: 1024,
          padding: "34px 42px 38px",
          borderRadius: 28,
          backgroundColor: "rgba(255,255,255,0.94)",
          border: "1px solid rgba(125,23,48,0.14)",
          boxShadow: "0 34px 100px rgba(60,13,24,0.17)",
          textAlign: "center",
          opacity: titleOut,
        }}
      >
        <div
          style={{
            color: FINAL_COLORS.burgundy,
            fontSize: 18,
            fontWeight: 840,
            letterSpacing: "0.17em",
            textTransform: "uppercase",
          }}
        >
          WebMCP Challenge Submission
        </div>
        <div
          style={{
            marginTop: 16,
            color: FINAL_COLORS.ink,
            fontSize: 92,
            lineHeight: 0.96,
            fontWeight: 800,
            letterSpacing: "-0.06em",
          }}
        >
          OrgMemory
        </div>
        <div style={{ marginTop: 19, color: "rgba(23,11,14,0.62)", fontSize: 29, lineHeight: 1.3 }}>
          Give every engineering change its full company context.
        </div>
      </Interactive.Div>

      <Interactive.Div
        name="Knowledge sources"
        style={{
          position: "absolute",
          left: 184,
          right: 184,
          bottom: 140,
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: 14,
          opacity: stripIn,
          translate: interpolate(stripIn, [0, 1], ["0px 20px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        {sources.map((source, index) => (
          <div
            key={source}
            style={{
              minHeight: 116,
              display: "grid",
              placeItems: "center",
              borderRadius: 18,
              backgroundColor: "rgba(255,255,255,0.95)",
              border: "1px solid rgba(125,23,48,0.16)",
              boxShadow: "0 20px 60px rgba(52,14,22,0.10)",
              color: index < 2 ? FINAL_COLORS.burgundy : FINAL_COLORS.green,
              fontSize: 21,
              fontWeight: 840,
              letterSpacing: "0.12em",
            }}
          >
            {source}
          </div>
        ))}
      </Interactive.Div>
    </FinalSceneShell>
  );
};
