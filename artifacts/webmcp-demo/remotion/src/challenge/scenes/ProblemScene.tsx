import {
  AbsoluteFill,
  Easing,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptureBackground, SceneLabel, SceneShell } from "../SceneChrome";

const sources = ["POSTMORTEM", "SLACK THREAD", "ONE ENGINEER"];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const warning = spring({
    frame: frame - 13 * fps,
    fps,
    config: { damping: 20, stiffness: 105, mass: 0.9 },
    durationInFrames: 34,
  });

  return (
    <SceneShell backgroundColor="#fbf7f5">
      <CaptureBackground
        image="00-landing-hero.png"
        fromScale={1.0}
        toScale={1.035}
        position="center top"
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(251,247,245,0.02) 0%, rgba(251,247,245,0.04) 45%, rgba(251,247,245,0.92) 84%, #fbf7f5 100%)",
        }}
      />
      <SceneLabel index="01" label="The problem" />

      <Interactive.Div
        name="Opening claim strip"
        style={{
          position: "absolute",
          left: 610,
          top: 690,
          width: 700,
          height: 58,
          display: "grid",
          placeItems: "center",
          borderRadius: 12,
          backgroundColor: "rgba(251,247,245,0.98)",
          border: "1px solid rgba(125,23,48,0.10)",
          color: "#7d1730",
          fontSize: 16,
          fontWeight: 820,
          letterSpacing: "0.14em",
        }}
      >
        SOURCE-BACKED MEMORY • BEFORE ACTION
      </Interactive.Div>

      <Interactive.Div
        name="Scattered knowledge"
        style={{
          position: "absolute",
          left: 250,
          right: 250,
          bottom: 152,
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 16,
        }}
      >
        {sources.map((source, index) => {
          const progress = spring({
            frame: frame - (5.2 + index * 0.65) * fps,
            fps,
            config: { damping: 18, stiffness: 120, mass: 0.8 },
            durationInFrames: 28,
          });
          return (
            <Interactive.Div
              key={source}
              name={source}
              style={{
                minHeight: 106,
                display: "grid",
                placeItems: "center",
                borderRadius: 18,
                backgroundColor: "rgba(255,255,255,0.90)",
                border: "1px solid rgba(125,23,48,0.18)",
                boxShadow: "0 18px 54px rgba(52,14,22,0.10)",
                color: "#681429",
                fontSize: 22,
                fontWeight: 820,
                letterSpacing: "0.13em",
                opacity: progress,
                translate: interpolate(progress, [0, 1], ["0px 18px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              {source}
            </Interactive.Div>
          );
        })}
      </Interactive.Div>

      <Interactive.Div
        name="Failure warning"
        style={{
          position: "absolute",
          left: 514,
          top: 704,
          width: 892,
          padding: "20px 26px",
          borderRadius: 18,
          backgroundColor: "#7d1730",
          color: "#fff9f7",
          boxShadow: "0 22px 70px rgba(89,13,32,0.24)",
          textAlign: "center",
          fontSize: 30,
          lineHeight: 1.2,
          fontWeight: 760,
          letterSpacing: "-0.02em",
          opacity: warning,
          scale: interpolate(warning, [0, 1], [0.97, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          translate: interpolate(warning, [0, 1], ["0px 14px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        Agent starts from zero <span style={{ padding: "0 10px" }}>→</span> repeats the outage
      </Interactive.Div>
    </SceneShell>
  );
};
