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

const tiers = [
  { name: "READ", detail: "Permission-trimmed to team scope", tone: FINAL_COLORS.green },
  { name: "REPORT OUTCOME", detail: "Append-only ledger entry", tone: "#385b72" },
  { name: "PROPOSE MEMORY", detail: "Human review required", tone: FINAL_COLORS.burgundy },
];

export const FinalApprovalsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const request = spring({
    frame: frame - 1.4 * fps,
    fps,
    durationInFrames: 34,
    config: { damping: 21, stiffness: 104, mass: 0.88 },
  });

  return (
    <FinalSceneShell route="/approvals" label="Human review">
      <FinalCapture image="19-approvals.png" brightness={0.74} fromScale={1} toScale={1.02} />
      <AbsoluteFill style={{ backgroundColor: "rgba(251,247,245,0.35)" }} />

      <Interactive.Div
        name="Approval queue"
        style={{
          position: "absolute",
          left: 152,
          top: 132,
          width: 1616,
          height: 548,
          padding: "30px 34px",
          borderRadius: 28,
          backgroundColor: "rgba(255,255,255,0.97)",
          border: "1px solid rgba(125,23,48,0.15)",
          boxShadow: "0 34px 100px rgba(65,18,28,0.15)",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ color: FINAL_COLORS.burgundy, fontSize: 16, fontWeight: 850, letterSpacing: "0.14em" }}>RUNBOOK ACTIONS</div>
            <div style={{ marginTop: 9, fontSize: 44, fontWeight: 790, letterSpacing: "-0.045em" }}>Approvals</div>
            <div style={{ marginTop: 8, color: "rgba(23,11,14,0.57)", fontSize: 21 }}>Requests wait here for a human decision.</div>
          </div>
          <span style={{ padding: "10px 14px", borderRadius: 999, backgroundColor: "rgba(125,23,48,0.08)", color: FINAL_COLORS.burgundy, fontSize: 16, fontWeight: 820, letterSpacing: "0.08em" }}>
            1 WAITING
          </span>
        </div>

        <Interactive.Div
          name="Pending payments restart"
          style={{
            marginTop: 25,
            padding: "24px 26px",
            borderRadius: 20,
            backgroundColor: "#fffdfc",
            border: "2px solid rgba(125,23,48,0.24)",
            boxShadow: "0 22px 66px rgba(74,18,31,0.10)",
            opacity: request,
            translate: interpolate(request, [0, 1], ["0px 18px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        >
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 30, alignItems: "center" }}>
            <div>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <span style={{ padding: "7px 10px", borderRadius: 999, backgroundColor: FINAL_COLORS.burgundy, color: "white", fontSize: 14, fontWeight: 850, letterSpacing: "0.10em" }}>
                  REQUIRES APPROVAL
                </span>
                <span style={{ color: "rgba(23,11,14,0.48)", fontFamily: "SFMono-Regular, Menlo, Consolas, monospace", fontSize: 15 }}>brf_pay_028</span>
              </div>
              <div style={{ marginTop: 16, fontSize: 34, fontWeight: 780, letterSpacing: "-0.035em" }}>
                Restart the payments connection pool
              </div>
              <div style={{ marginTop: 10, color: "rgba(23,11,14,0.62)", fontSize: 20, lineHeight: 1.35 }}>
                2 incidents · concurrency cap · shared Postgres blast radius · first-response procedure
              </div>
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button style={{ border: 0, borderRadius: 12, padding: "15px 22px", backgroundColor: FINAL_COLORS.green, color: "white", fontFamily: "inherit", fontSize: 18, fontWeight: 820 }}>Approve</button>
              <button style={{ border: "1px solid rgba(125,23,48,0.28)", borderRadius: 12, padding: "15px 22px", backgroundColor: "white", color: FINAL_COLORS.burgundy, fontFamily: "inherit", fontSize: 18, fontWeight: 820 }}>Deny</button>
            </div>
          </div>
          <div style={{ marginTop: 18, paddingTop: 15, borderTop: "1px solid rgba(125,23,48,0.10)", color: FINAL_COLORS.burgundy, fontSize: 17, fontWeight: 740 }}>
            OrgMemory does not approve its own recommendation.
          </div>
        </Interactive.Div>
      </Interactive.Div>

      <div style={{ position: "absolute", left: 188, right: 188, bottom: 140, display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        {tiers.map((tier, index) => {
          const progress = spring({
            frame: frame - (8.0 + index * 1.3) * fps,
            fps,
            durationInFrames: 30,
            config: { damping: 20, stiffness: 110, mass: 0.84 },
          });
          return (
            <Interactive.Div
              key={tier.name}
              name={tier.name}
              style={{
                minHeight: 160,
                padding: "23px 25px",
                borderRadius: 20,
                backgroundColor: "rgba(255,255,255,0.97)",
                border: `1px solid ${tier.tone}38`,
                boxShadow: "0 22px 66px rgba(52,14,22,0.10)",
                opacity: progress,
                translate: interpolate(progress, [0, 1], ["0px 16px", "0px 0px"], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <span style={{ display: "inline-flex", padding: "7px 10px", borderRadius: 999, backgroundColor: tier.tone, color: "white", fontSize: 14, fontWeight: 850, letterSpacing: "0.10em" }}>
                {tier.name}
              </span>
              <div style={{ marginTop: 18, color: FINAL_COLORS.ink, fontSize: 25, lineHeight: 1.18, fontWeight: 750, letterSpacing: "-0.025em" }}>
                {tier.detail}
              </div>
            </Interactive.Div>
          );
        })}
      </div>
    </FinalSceneShell>
  );
};
