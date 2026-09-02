import {
  AbsoluteFill,
  Interactive,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { CaptureBackground, SceneLabel, SceneShell } from "../SceneChrome";

const tiers = [
  { name: "READ", detail: "Permission-trimmed to team scope", tone: "#174f3c" },
  { name: "REPORT OUTCOME", detail: "Append-only; changes no knowledge", tone: "#385b72" },
  { name: "PROPOSE MEMORY", detail: "Human approval required", tone: "#7d1730" },
];

export const PermissionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <SceneShell backgroundColor="#fbf7f5">
      <CaptureBackground image="19-approvals.png" brightness={0.72} fromScale={1.0} toScale={1.025} />
      <AbsoluteFill style={{ backgroundColor: "rgba(251,247,245,0.32)" }} />
      <SceneLabel index="04" label="The permission boundary" />
      <Interactive.Div
        name="Boundary headline"
        style={{
          position: "absolute",
          left: 182,
          top: 146,
          width: 980,
          padding: "26px 30px 28px",
          borderRadius: 22,
          backgroundColor: "rgba(255,255,255,0.94)",
          border: "1px solid rgba(125,23,48,0.15)",
          boxShadow: "0 24px 72px rgba(65,18,28,0.12)",
        }}
      >
        <div
          style={{
            color: "#7d1730",
            fontSize: 52,
            lineHeight: 1.02,
            fontWeight: 790,
            letterSpacing: "-0.05em",
          }}
        >
          Capability is never authorization.
        </div>
        <div
          style={{
            marginTop: 13,
            color: "rgba(19,9,11,0.62)",
            fontSize: 24,
            lineHeight: 1.35,
          }}
        >
          OrgMemory can surface a decision. Only a person can approve it.
        </div>
      </Interactive.Div>

      <div
        style={{
          position: "absolute",
          left: 182,
          right: 182,
          bottom: 160,
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
        }}
      >
        {tiers.map((tier, index) => {
          const progress = spring({
            frame: frame - (5.8 + index * 1.15) * fps,
            fps,
            config: { damping: 19, stiffness: 112, mass: 0.84 },
            durationInFrames: 32,
          });
          return (
            <Interactive.Div
              key={tier.name}
              name={tier.name}
              style={{
                minHeight: 190,
                padding: "27px 28px",
                borderRadius: 22,
                backgroundColor: "rgba(255,255,255,0.96)",
                border: `1px solid ${tier.tone}35`,
                boxShadow: "0 24px 70px rgba(52,14,22,0.11)",
                opacity: progress,
                translate: interpolate(progress, [0, 1], ["0px 18px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <div
                style={{
                  display: "inline-flex",
                  padding: "8px 11px",
                  borderRadius: 999,
                  backgroundColor: tier.tone,
                  color: "white",
                  fontSize: 15,
                  fontWeight: 850,
                  letterSpacing: "0.11em",
                }}
              >
                {tier.name}
              </div>
              <div
                style={{
                  marginTop: 22,
                  color: "#251014",
                  fontSize: 27,
                  lineHeight: 1.18,
                  fontWeight: 740,
                  letterSpacing: "-0.025em",
                }}
              >
                {tier.detail}
              </div>
            </Interactive.Div>
          );
        })}
      </div>
    </SceneShell>
  );
};
