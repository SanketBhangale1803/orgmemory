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

const task = "restart the payments connection pool";

const evidence = [
  { type: "INCIDENT", title: "Pool exhaustion during recovery", id: "mem_inc_4f19" },
  { type: "INCIDENT", title: "Restart amplified checkout timeouts", id: "mem_inc_79fc" },
  { type: "DECISION", title: "Cap payments worker concurrency", id: "mem_dec_146a" },
  { type: "BLAST RADIUS", title: "Shared Postgres cluster with ledger", id: "mem_dep_8a69" },
  { type: "PROCEDURE", title: "Drain traffic, inspect saturation first", id: "mem_run_011f" },
];

export const BriefingScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typedChars = Math.floor(
    interpolate(frame, [1.3 * fps, 5.8 * fps], [0, task.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }),
  );
  const resultProgress = spring({
    frame: frame - 8.2 * fps,
    fps,
    config: { damping: 22, stiffness: 100, mass: 0.92 },
    durationInFrames: 34,
  });
  const proceedProgress = spring({
    frame: frame - 51 * fps,
    fps,
    config: { damping: 20, stiffness: 110, mass: 0.84 },
    durationInFrames: 30,
  });

  return (
    <SceneShell>
      <CaptureBackground image="01-command-center.png" brightness={0.22} blur={8} toScale={1.06} />
      <AbsoluteFill style={{ backgroundColor: "rgba(1,7,6,0.60)" }} />
      <SceneLabel index="03" label="The briefing" dark />

      <Interactive.Div
        name="Briefing console"
        style={{
          position: "absolute",
          left: 146,
          top: 138,
          width: 1628,
          height: 822,
          padding: "34px 38px",
          borderRadius: 28,
          backgroundColor: "rgba(4,13,11,0.94)",
          border: "1px solid rgba(157,244,211,0.24)",
          boxShadow: "0 40px 120px rgba(0,0,0,0.54)",
          color: "#f4fffb",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div
              style={{
                color: "#9df4d3",
                fontSize: 17,
                fontWeight: 820,
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              get_orgmemory_briefing
            </div>
            <div
              style={{
                marginTop: 8,
                fontSize: 34,
                fontWeight: 760,
                letterSpacing: "-0.035em",
              }}
            >
              Ask before you act
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
              fontWeight: 720,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            deterministic • no model
          </div>
        </div>

        <div
          style={{
            marginTop: 26,
            display: "grid",
            gridTemplateColumns: "1fr 230px 154px",
            gap: 12,
          }}
        >
          <div
            style={{
              minHeight: 62,
              padding: "16px 18px",
              borderRadius: 14,
              backgroundColor: "rgba(255,255,255,0.055)",
              border: "1px solid rgba(255,255,255,0.12)",
              fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
              fontSize: 22,
              color: "#f4fffb",
            }}
          >
            {task.slice(0, typedChars)}
            <span
              style={{
                opacity: interpolate(frame % 24, [0, 11, 12, 23], [1, 1, 0, 0]),
                color: "#9df4d3",
              }}
            >
              ▍
            </span>
          </div>
          <div
            style={{
              padding: "17px 18px",
              borderRadius: 14,
              backgroundColor: "rgba(255,255,255,0.055)",
              border: "1px solid rgba(255,255,255,0.12)",
              color: "rgba(235,249,243,0.78)",
              fontSize: 21,
              fontWeight: 680,
            }}
          >
            payments
          </div>
          <div
            style={{
              display: "grid",
              placeItems: "center",
              borderRadius: 14,
              backgroundColor: frame < 7.5 * fps ? "#174f3c" : "#9df4d3",
              color: frame < 7.5 * fps ? "#dffff3" : "#06100e",
              fontSize: 20,
              fontWeight: 820,
            }}
          >
            {frame < 7.5 * fps ? "Brief me" : "Briefed ✓"}
          </div>
        </div>

        <Interactive.Div
          name="Briefing result"
          style={{
            marginTop: 24,
            display: "grid",
            gridTemplateColumns: "390px 1fr",
            gap: 22,
            opacity: resultProgress,
            translate: interpolate(resultProgress, [0, 1], ["0px 18px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        >
          <div
            style={{
              padding: "24px",
              borderRadius: 20,
              backgroundColor: "rgba(125,23,48,0.22)",
              border: "1px solid rgba(255,137,164,0.42)",
            }}
          >
            <div
              style={{
                display: "inline-flex",
                padding: "9px 13px",
                borderRadius: 999,
                backgroundColor: "#a72949",
                color: "#fff9fb",
                fontSize: 16,
                fontWeight: 850,
                letterSpacing: "0.12em",
              }}
            >
              REQUIRES APPROVAL
            </div>
            <div
              style={{
                marginTop: 20,
                fontSize: 31,
                lineHeight: 1.12,
                fontWeight: 780,
                letterSpacing: "-0.035em",
              }}
            >
              Production state change detected.
            </div>
            <div
              style={{
                marginTop: 16,
                color: "rgba(238,247,244,0.68)",
                fontSize: 20,
                lineHeight: 1.35,
              }}
            >
              Read the constraints below, then get an explicit human decision.
            </div>
            <div
              style={{
                marginTop: 20,
                paddingTop: 16,
                borderTop: "1px solid rgba(255,255,255,0.12)",
                color: "#9df4d3",
                fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
                fontSize: 17,
              }}
            >
              briefing_id: brf_pay_028
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {evidence.map((item, index) => {
              const progress = spring({
                frame: frame - (12 + index * 3.2) * fps,
                fps,
                config: { damping: 20, stiffness: 100, mass: 0.9 },
                durationInFrames: 28,
              });
              return (
                <Interactive.Div
                  key={item.id}
                  name={`${item.type} ${item.id}`}
                  style={{
                    minHeight: index === 4 ? 124 : 112,
                    gridColumn: index === 4 ? "1 / span 2" : undefined,
                    padding: "17px 19px",
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
                  <div
                    style={{
                      color: "#9df4d3",
                      fontSize: 13,
                      fontWeight: 850,
                      letterSpacing: "0.12em",
                    }}
                  >
                    {item.type}
                  </div>
                  <div style={{ marginTop: 7, fontSize: 21, fontWeight: 720 }}>{item.title}</div>
                  <div
                    style={{
                      marginTop: 8,
                      color: "rgba(225,244,237,0.52)",
                      fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
                      fontSize: 14,
                    }}
                  >
                    {item.id} ↗
                  </div>
                </Interactive.Div>
              );
            })}
          </div>
        </Interactive.Div>

        <Interactive.Div
          name="Read-only boundary"
          style={{
            position: "absolute",
            right: 38,
            bottom: 32,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "14px 18px",
            borderRadius: 14,
            backgroundColor: "rgba(8,67,47,0.96)",
            border: "1px solid rgba(157,244,211,0.38)",
            boxShadow: "0 18px 54px rgba(0,0,0,0.30)",
            color: "#eafff7",
            opacity: proceedProgress,
            scale: interpolate(proceedProgress, [0, 1], [0.96, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <span style={{ color: "rgba(224,255,244,0.65)", fontSize: 16 }}>
            read-only intent
          </span>
          <strong style={{ color: "#9df4d3", fontSize: 19, letterSpacing: "0.1em" }}>
            PROCEED
          </strong>
        </Interactive.Div>
      </Interactive.Div>
    </SceneShell>
  );
};
