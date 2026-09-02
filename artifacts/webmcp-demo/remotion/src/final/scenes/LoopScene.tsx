import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  Interactive,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { FINAL_COLORS } from "../constants";
import { FinalCapture, FinalSceneShell, ToolNameChip } from "../FinalChrome";

const flow = ["CONTEXT SERVED", "ACTION TAKEN", "OUTCOME OBSERVED"];

export const FinalLoopScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const closeProgress = interpolate(frame, [8.5 * fps, 10.0 * fps], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const receipt = spring({
    frame: frame - 11 * fps,
    fps,
    durationInFrames: 32,
    config: { damping: 20, stiffness: 108, mass: 0.85 },
  });

  return (
    <FinalSceneShell route="/loop" label="Outcome ledger">
      <FinalCapture image="18-outcome-loop.png" brightness={0.74} fromScale={1} toScale={1.022} />
      <CanvasImage
        src={staticFile("captures/20-outcome-closed.png")}
        width={1920}
        height={1080}
        style={{ width: 1920, height: 1080, objectFit: "cover", opacity: closeProgress }}
      />
      <AbsoluteFill style={{ backgroundColor: "rgba(251,247,245,0.30)" }} />

      <Interactive.Div
        name="Outcome operation"
        style={{
          position: "absolute",
          left: 128,
          top: 128,
          width: 1664,
          minHeight: 300,
          padding: "28px 32px",
          borderRadius: 26,
          backgroundColor: "rgba(4,13,11,0.96)",
          border: "1px solid rgba(157,244,211,0.28)",
          boxShadow: "0 38px 110px rgba(0,0,0,0.44)",
          color: "#f5fffb",
        }}
      >
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1.05fr", gap: 26, alignItems: "stretch" }}>
          <div>
            <ToolNameChip name="record_orgmemory_outcome" />
            <div style={{ marginTop: 18, fontSize: 39, lineHeight: 1.05, fontWeight: 780, letterSpacing: "-0.045em" }}>
              Close the loop after acting.
            </div>
            <div style={{ marginTop: 14, color: "rgba(229,247,240,0.64)", fontSize: 20, lineHeight: 1.35 }}>
              Appends to the outcome ledger. Company memory is unchanged.
            </div>
          </div>
          <div
            style={{
              padding: "19px 21px",
              borderRadius: 16,
              backgroundColor: "rgba(255,255,255,0.055)",
              border: "1px solid rgba(255,255,255,0.12)",
              fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
              fontSize: 17,
              lineHeight: 1.52,
              color: "rgba(239,253,247,0.82)",
            }}
          >
            <div><span style={{ color: FINAL_COLORS.mint }}>briefing_id:</span> "brf_pay_028"</div>
            <div><span style={{ color: FINAL_COLORS.mint }}>action:</span> "followed_procedure"</div>
            <div><span style={{ color: FINAL_COLORS.mint }}>outcome:</span> "succeeded"</div>
            <div><span style={{ color: FINAL_COLORS.mint }}>target:</span> "payments"</div>
          </div>
        </div>
        <Interactive.Div
          name="Outcome receipt"
          style={{
            marginTop: 18,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "14px 17px",
            borderRadius: 14,
            backgroundColor: "rgba(23,79,60,0.92)",
            border: "1px solid rgba(157,244,211,0.30)",
            opacity: receipt,
            translate: interpolate(receipt, [0, 1], ["0px 12px", "0px 0px"], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        >
          <strong style={{ color: FINAL_COLORS.mint, fontSize: 19, letterSpacing: "0.08em" }}>RECORDED • SUCCEEDED</strong>
          <span style={{ color: "rgba(237,255,248,0.72)", fontSize: 18 }}>context row closed · reward +1</span>
        </Interactive.Div>
      </Interactive.Div>

      <div style={{ position: "absolute", left: 205, right: 205, bottom: 146, display: "grid", gridTemplateColumns: "1fr auto 1fr auto 1fr", gap: 16, alignItems: "center" }}>
        {flow.map((item, index) => {
          const progress = spring({
            frame: frame - (5.0 + index * 2.2) * fps,
            fps,
            durationInFrames: 30,
            config: { damping: 19, stiffness: 112, mass: 0.82 },
          });
          return (
            <div key={item} style={{ display: "contents" }}>
              <Interactive.Div
                name={item}
                style={{
                  minHeight: 120,
                  display: "grid",
                  placeItems: "center",
                  padding: "18px",
                  borderRadius: 19,
                  backgroundColor: index === 2 ? FINAL_COLORS.green : "rgba(255,255,255,0.97)",
                  border: index === 2 ? "1px solid rgba(23,79,60,0.38)" : "1px solid rgba(125,23,48,0.17)",
                  boxShadow: "0 22px 64px rgba(52,14,22,0.12)",
                  color: index === 2 ? "#effff9" : "#5b1224",
                  fontSize: 20,
                  fontWeight: 850,
                  letterSpacing: "0.10em",
                  textAlign: "center",
                  opacity: progress,
                  scale: interpolate(progress, [0, 1], [0.96, 1], {
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  }),
                }}
              >
                {item}
              </Interactive.Div>
              {index < flow.length - 1 ? <div style={{ color: FINAL_COLORS.burgundy, fontSize: 38, fontWeight: 860 }}>→</div> : null}
            </div>
          );
        })}
      </div>
    </FinalSceneShell>
  );
};
