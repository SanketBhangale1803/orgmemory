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

const metrics = [
  ["21", "browser-native tools"],
  ["14", "read-only"],
  ["6", "human-governed"],
];

export const BuiltScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <SceneShell>
      <CaptureBackground image="01-command-center.png" brightness={0.34} blur={3} />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 54%, rgba(19,61,49,0.26), rgba(2,8,7,0.78) 72%)",
        }}
      />
      <SceneLabel index="02" label="What we built" dark />
      <Interactive.Div
        name="Memory layer headline"
        style={{
          position: "absolute",
          left: 150,
          top: 184,
          width: 1110,
          color: "#f5fffb",
          opacity: interpolate(frame, [0, 24], [0, 1], {
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
            fontWeight: 820,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
          }}
        >
          Time-aware • evidence-backed • session-native
        </div>
        <div
          style={{
            marginTop: 18,
            fontSize: 86,
            lineHeight: 0.98,
            fontWeight: 780,
            letterSpacing: "-0.055em",
          }}
        >
          The memory layer for engineering organizations.
        </div>
        <div
          style={{
            marginTop: 24,
            width: 930,
            color: "rgba(230,246,240,0.74)",
            fontSize: 29,
            lineHeight: 1.34,
          }}
        >
          The page registers the tools against its authenticated session. The agent never sees a credential.
        </div>
      </Interactive.Div>

      <div
        style={{
          position: "absolute",
          left: 150,
          right: 150,
          bottom: 112,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 18,
        }}
      >
        {metrics.map(([value, label], index) => {
          const progress = spring({
            frame: frame - (8.5 + index * 0.75) * fps,
            fps,
            config: { damping: 19, stiffness: 110, mass: 0.86 },
            durationInFrames: 32,
          });
          return (
            <Interactive.Div
              key={label}
              name={`${value} ${label}`}
              style={{
                minHeight: 194,
                padding: "30px 34px",
                borderRadius: 24,
                backgroundColor: "rgba(3,13,10,0.88)",
                border: "1px solid rgba(157,244,211,0.26)",
                boxShadow: "0 28px 80px rgba(0,0,0,0.36)",
                opacity: progress,
                scale: interpolate(progress, [0, 1], [0.96, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <div
                style={{
                  color: "white",
                  fontSize: 78,
                  lineHeight: 0.9,
                  fontWeight: 820,
                  letterSpacing: "-0.06em",
                }}
              >
                {value}
              </div>
              <div
                style={{
                  marginTop: 22,
                  color: "#9df4d3",
                  fontSize: 20,
                  fontWeight: 780,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                {label}
              </div>
            </Interactive.Div>
          );
        })}
      </div>
    </SceneShell>
  );
};
