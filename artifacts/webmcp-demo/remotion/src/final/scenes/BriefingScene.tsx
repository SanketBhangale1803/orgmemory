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

const task = "Restart the payments connection pool";
const evidence = [
  { type: "INCIDENT", title: "Pool exhaustion during recovery", id: "mem_inc_4f19" },
  { type: "INCIDENT", title: "Restart amplified checkout timeouts", id: "mem_inc_79fc" },
  { type: "DECISION", title: "Cap payments worker concurrency", id: "mem_dec_146a" },
  { type: "BLAST RADIUS", title: "Shared Postgres cluster with ledger", id: "mem_dep_8a69" },
  { type: "PROCEDURE", title: "Drain traffic, inspect saturation first", id: "mem_run_011f" },
];

export const FinalBriefingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typedChars = Math.floor(
    interpolate(frame, [1.4 * fps, 6.2 * fps], [0, task.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const selected = frame > 5.6 * fps;
  const result = spring({
    frame: frame - 8.0 * fps,
    fps,
    durationInFrames: 36,
    config: { damping: 22, stiffness: 100, mass: 0.9 },
  });
  const sourceOpen = spring({
    frame: frame - 34 * fps,
    fps,
    durationInFrames: 30,
    config: { damping: 20, stiffness: 110, mass: 0.84 },
  });

  return (
    <FinalSceneShell route="/webmcp" label="Live briefing" dark>
      <FinalCapture image="03-real-tool-discovery.png" brightness={0.28} blur={8} toScale={1.045} />
      <AbsoluteFill style={{ backgroundColor: "rgba(1,7,6,0.62)" }} />

      <Interactive.Div
        name="Briefing console"
        style={{
          position: "absolute",
          left: 124,
          top: 126,
          width: 1672,
          height: 836,
          padding: "30px 34px",
          borderRadius: 28,
          backgroundColor: "rgba(4,13,11,0.95)",
          border: "1px solid rgba(157,244,211,0.25)",
          boxShadow: "0 42px 124px rgba(0,0,0,0.56)",
          color: "#f4fffb",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <ToolNameChip name="get_orgmemory_briefing" />
            <div style={{ marginTop: 12, fontSize: 31, fontWeight: 770, letterSpacing: "-0.035em" }}>
              Evaluate an intended action
            </div>
          </div>
          <div
            style={{
              padding: "9px 14px",
              borderRadius: 999,
              backgroundColor: "rgba(157,244,211,0.08)",
              border: "1px solid rgba(157,244,211,0.20)",
              color: "rgba(222,246,237,0.76)",
              fontSize: 15,
              fontWeight: 760,
              letterSpacing: "0.09em",
              textTransform: "uppercase",
            }}
          >
            signed-in scope • payments
          </div>
        </div>

        <div style={{ marginTop: 22, display: "grid", gridTemplateColumns: "1fr 238px 160px", gap: 12 }}>
          <div
            style={{
              minHeight: 62,
              padding: "16px 18px",
              borderRadius: 14,
              backgroundColor: "rgba(255,255,255,0.055)",
              border: "1px solid rgba(255,255,255,0.12)",
              fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
              fontSize: 22,
            }}
          >
            {task.slice(0, typedChars)}
            <span style={{ color: FINAL_COLORS.mint, opacity: interpolate(frame % 24, [0, 11, 12, 23], [1, 1, 0, 0]) }}>▍</span>
          </div>
          <div
            style={{
              padding: "17px 18px",
              borderRadius: 14,
              backgroundColor: "rgba(255,255,255,0.055)",
              border: "1px solid rgba(255,255,255,0.12)",
              color: "rgba(235,249,243,0.78)",
              fontSize: 21,
              fontWeight: 700,
            }}
          >
            payments ▾
          </div>
          <div
            style={{
              display: "grid",
              placeItems: "center",
              borderRadius: 14,
              backgroundColor: selected ? FINAL_COLORS.mint : FINAL_COLORS.green,
              color: selected ? FINAL_COLORS.deep : "#eafff7",
              fontSize: 20,
              fontWeight: 840,
            }}
          >
            {selected ? "Briefed ✓" : "Brief me"}
          </div>
        </div>

        <Interactive.Div
          name="Briefing result"
          style={{
            marginTop: 22,
            display: "grid",
            gridTemplateColumns: "382px 1fr",
            gap: 20,
            opacity: result,
            translate: interpolate(result, [0, 1], ["0px 18px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        >
          <div
            style={{
              padding: "22px",
              borderRadius: 20,
              backgroundColor: "rgba(125,23,48,0.23)",
              border: "1px solid rgba(255,137,164,0.43)",
            }}
          >
            <div
              style={{
                display: "inline-flex",
                padding: "9px 13px",
                borderRadius: 999,
                backgroundColor: FINAL_COLORS.burgundyBright,
                color: "#fff9fb",
                fontSize: 16,
                fontWeight: 860,
                letterSpacing: "0.12em",
              }}
            >
              REQUIRES APPROVAL
            </div>
            <div style={{ marginTop: 18, fontSize: 29, lineHeight: 1.12, fontWeight: 780, letterSpacing: "-0.035em" }}>
              Production state change detected.
            </div>
            <div style={{ marginTop: 15, color: "rgba(238,247,244,0.68)", fontSize: 19, lineHeight: 1.35 }}>
              Read the constraints below, then get an explicit human decision.
            </div>
            <div
              style={{
                marginTop: 18,
                paddingTop: 15,
                borderTop: "1px solid rgba(255,255,255,0.12)",
                color: FINAL_COLORS.mint,
                fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
                fontSize: 16,
              }}
            >
              briefing_id: brf_pay_028
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 11 }}>
            {evidence.map((item, index) => {
              const progress = spring({
                frame: frame - (11 + index * 3.0) * fps,
                fps,
                durationInFrames: 28,
                config: { damping: 20, stiffness: 102, mass: 0.88 },
              });
              return (
                <Interactive.Div
                  key={item.id}
                  name={`${item.type} ${item.id}`}
                  style={{
                    minHeight: index === 4 ? 116 : 107,
                    gridColumn: index === 4 ? "1 / span 2" : undefined,
                    padding: "15px 18px",
                    borderRadius: 16,
                    backgroundColor: "rgba(255,255,255,0.048)",
                    border: "1px solid rgba(157,244,211,0.13)",
                    opacity: progress,
                    translate: interpolate(progress, [0, 1], ["10px 0px", "0px 0px"], {
                      extrapolateLeft: "clamp",
                      extrapolateRight: "clamp",
                    }),
                  }}
                >
                  <div style={{ color: FINAL_COLORS.mint, fontSize: 13, fontWeight: 860, letterSpacing: "0.12em" }}>
                    {item.type}
                  </div>
                  <div style={{ marginTop: 6, fontSize: 20, fontWeight: 730 }}>{item.title}</div>
                  <div style={{ marginTop: 7, color: "rgba(225,244,237,0.52)", fontFamily: "SFMono-Regular, Menlo, Consolas, monospace", fontSize: 14 }}>
                    {item.id} ↗
                  </div>
                </Interactive.Div>
              );
            })}
          </div>
        </Interactive.Div>

        <Interactive.Div
          name="Evidence source opened"
          style={{
            position: "absolute",
            right: 50,
            bottom: 38,
            width: 720,
            padding: "16px 19px",
            borderRadius: 15,
            backgroundColor: "rgba(7,18,15,0.98)",
            border: "1px solid rgba(157,244,211,0.36)",
            boxShadow: "0 22px 70px rgba(0,0,0,0.40)",
            opacity: sourceOpen,
            translate: interpolate(sourceOpen, [0, 1], ["0px 14px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <div style={{ color: FINAL_COLORS.mint, fontSize: 14, fontWeight: 840, letterSpacing: "0.11em" }}>ORIGINAL EVIDENCE OPENED</div>
          <div style={{ marginTop: 8, fontSize: 20, fontWeight: 720 }}>Payments incident review · January 2026</div>
          <div style={{ marginTop: 6, color: "rgba(230,248,241,0.60)", fontSize: 16 }}>mem_inc_79fc → cited source chunk 04</div>
        </Interactive.Div>
      </Interactive.Div>
    </FinalSceneShell>
  );
};
