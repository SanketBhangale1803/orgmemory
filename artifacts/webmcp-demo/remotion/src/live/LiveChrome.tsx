import {
  AbsoluteFill,
  CanvasImage,
  Easing,
  Interactive,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { LIVE_COLORS } from "./constants";

type Highlight = {
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
};

export const LiveScene: React.FC<{
  image: string;
  route: string;
  kicker: string;
  title: string;
  body: string;
  highlights?: Highlight[];
  dark?: boolean;
  children?: React.ReactNode;
}> = ({ image, route, kicker, title, body, highlights = [], dark = false, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, 12, durationInFrames - 12, durationInFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, durationInFrames], [1.005, 1.028], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.22, 0.74, 0.2, 1),
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: dark ? LIVE_COLORS.deep : LIVE_COLORS.paper,
        color: dark ? "#f6fff9" : LIVE_COLORS.ink,
        fontFamily: '"OrgMemory Sans", Arial, sans-serif',
        opacity,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: dark
            ? "radial-gradient(circle at 30% 20%, rgba(157,244,211,0.11), transparent 42%), #07110f"
            : "radial-gradient(circle at 28% 18%, rgba(142,35,59,0.08), transparent 44%)",
        }}
      />

      <div style={{ position: "absolute", left: 48, top: 38, display: "flex", alignItems: "center", gap: 15 }}>
        <div style={{ width: 31, height: 31, color: dark ? LIVE_COLORS.mint : LIVE_COLORS.burgundy, fontSize: 31, fontWeight: 900 }}>⌁</div>
        <div style={{ fontSize: 21, fontWeight: 820, letterSpacing: "-0.025em" }}>OrgMemory</div>
        <div
          style={{
            marginLeft: 12,
            padding: "7px 11px",
            borderRadius: 999,
            border: dark ? "1px solid rgba(157,244,211,0.25)" : "1px solid rgba(142,35,59,0.17)",
            color: dark ? LIVE_COLORS.mint : LIVE_COLORS.burgundy,
            fontSize: 15,
            fontWeight: 760,
            letterSpacing: "0.05em",
          }}
        >
          LIVE PRODUCTION
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          right: 48,
          top: 39,
          padding: "8px 13px",
          borderRadius: 9,
          backgroundColor: dark ? "rgba(255,255,255,0.08)" : "rgba(142,35,59,0.07)",
          color: dark ? "rgba(255,255,255,0.76)" : "rgba(23,11,14,0.62)",
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: 16,
        }}
      >
        orgmemory.vercel.app{route}
      </div>

      <div
        style={{
          position: "absolute",
          left: 48,
          top: 112,
          width: 1328,
          height: 747,
          borderRadius: 22,
          overflow: "hidden",
          border: dark ? "1px solid rgba(157,244,211,0.20)" : "1px solid rgba(88,26,40,0.17)",
          boxShadow: dark ? "0 34px 100px rgba(0,0,0,0.46)" : "0 34px 100px rgba(80,22,35,0.16)",
          backgroundColor: "white",
        }}
      >
        <CanvasImage
          src={staticFile(`captures/live/${image}`)}
          width={1920}
          height={1080}
          style={{ width: 1328, height: 747, objectFit: "cover", scale }}
        />
        {highlights.map((item, index) => {
          const progress = interpolate(frame, [18 + index * 10, 34 + index * 10], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });
          return (
            <div
              key={`${item.x}-${item.y}`}
              style={{
                position: "absolute",
                left: item.x * (1328 / 1920),
                top: item.y * (747 / 1080),
                width: item.width * (1328 / 1920),
                height: item.height * (747 / 1080),
                borderRadius: 11,
                border: `3px solid ${LIVE_COLORS.burgundy}`,
                backgroundColor: "rgba(142,35,59,0.025)",
                boxShadow: "0 0 0 8px rgba(142,35,59,0.08)",
                opacity: progress,
              }}
            >
              {item.label ? (
                <span
                  style={{
                    position: "absolute",
                    left: 10,
                    top: 10,
                    padding: "7px 9px",
                    borderRadius: 7,
                    backgroundColor: LIVE_COLORS.burgundy,
                    color: "white",
                    fontSize: 14,
                    fontWeight: 760,
                  }}
                >
                  {item.label}
                </span>
              ) : null}
            </div>
          );
        })}
        {children}
      </div>

      <Interactive.Div
        name="Narration rail"
        style={{
          position: "absolute",
          left: 1408,
          top: 112,
          width: 464,
          height: 747,
          padding: "40px 38px",
          boxSizing: "border-box",
          borderRadius: 22,
          backgroundColor: dark ? "rgba(255,255,255,0.055)" : LIVE_COLORS.burgundyDark,
          border: dark ? "1px solid rgba(157,244,211,0.20)" : "1px solid rgba(142,35,59,0.28)",
          boxShadow: "0 34px 100px rgba(33,7,14,0.22)",
          color: "#fff9fb",
        }}
      >
        <div style={{ color: LIVE_COLORS.mint, fontSize: 17, fontWeight: 820, letterSpacing: "0.13em", textTransform: "uppercase" }}>{kicker}</div>
        <div style={{ marginTop: 23, fontSize: 50, lineHeight: 0.99, fontWeight: 800, letterSpacing: "-0.055em" }}>{title}</div>
        <div style={{ marginTop: 26, color: "rgba(255,249,251,0.72)", fontSize: 28, lineHeight: 1.35, letterSpacing: "-0.018em" }}>{body}</div>
      </Interactive.Div>

      <div style={{ position: "absolute", left: 48, right: 48, bottom: 34, height: 3, borderRadius: 99, backgroundColor: dark ? "rgba(157,244,211,0.13)" : "rgba(142,35,59,0.10)" }}>
        <div style={{ width: `${(frame / Math.max(1, durationInFrames - 1)) * 100}%`, height: "100%", borderRadius: 99, backgroundColor: dark ? LIVE_COLORS.mint : LIVE_COLORS.burgundy }} />
      </div>
    </AbsoluteFill>
  );
};

export const FastForward: React.FC<{ label?: string }> = ({ label = "WAITING SKIPPED" }) => {
  const frame = useCurrentFrame();
  const pulse = interpolate(frame % 24, [0, 12, 24], [0.7, 1, 0.7]);
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "grid",
        placeItems: "center",
        backgroundColor: "rgba(7,17,15,0.65)",
        backdropFilter: "blur(4px)",
      }}
    >
      <div style={{ padding: "18px 24px", borderRadius: 14, backgroundColor: "rgba(7,17,15,0.93)", border: "1px solid rgba(157,244,211,0.45)", color: "white", fontSize: 23, fontWeight: 820, letterSpacing: "0.08em", opacity: pulse }}>
        ⏩&nbsp;&nbsp;{label}
      </div>
    </div>
  );
};
