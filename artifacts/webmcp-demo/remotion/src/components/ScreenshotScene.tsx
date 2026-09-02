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
import type { CalloutSpec, ScreenshotSceneProps } from "../types";

const ACCENT = "#9df4d3";

const Callout: React.FC<{ spec: CalloutSpec }> = ({ spec }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enterFrame = (spec.enterAt ?? 1.1) * fps;
  const progress = spring({
    frame: frame - enterFrame,
    fps,
    config: { damping: 18, stiffness: 120, mass: 0.8 },
    durationInFrames: 28,
  });
  const pulseFrame = Math.max(0, frame - enterFrame) % 54;

  return (
    <Interactive.Div
      name={`Callout — ${spec.label}`}
      style={{
        position: "absolute",
        left: `${(spec.x / 1920) * 100}%`,
        top: `${(spec.y / 1080) * 100}%`,
        width: `${(spec.width / 1920) * 100}%`,
        height: `${(spec.height / 1080) * 100}%`,
        border: `2px solid ${ACCENT}`,
        borderRadius: 18,
        backgroundColor: "rgba(157,244,211,0.045)",
        boxShadow: `0 0 0 ${interpolate(
          pulseFrame,
          [0, 27, 54],
          [0, 12, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        )}px rgba(157,244,211,0.07), 0 18px 60px rgba(0,0,0,0.28)`,
        opacity: progress,
        scale: interpolate(progress, [0, 1], [0.985, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        }),
      }}
    >
      <Interactive.Div
        name="Callout label"
        style={{
          position: "absolute",
          left: 14,
          top: 14,
          padding: "9px 13px",
          borderRadius: 10,
          backgroundColor: "rgba(4,12,10,0.92)",
          border: "1px solid rgba(157,244,211,0.32)",
          color: "#ecfff8",
          fontSize: 18,
          lineHeight: 1.15,
          fontWeight: 720,
          letterSpacing: "0.01em",
          whiteSpace: "nowrap",
        }}
      >
        {spec.label}
      </Interactive.Div>
    </Interactive.Div>
  );
};

export const ScreenshotScene: React.FC<ScreenshotSceneProps> = ({
  image,
  eyebrow,
  title,
  detail,
  timeRange,
  chapter,
  focusX = 0.5,
  focusY = 0.5,
  titleSide = "left",
  command,
  callouts = [],
  metrics = [],
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const headingLeft = titleSide === "left" ? 76 : 1034;

  return (
    <AbsoluteFill style={{ backgroundColor: "#06100e", overflow: "hidden" }}>
      <CanvasImage
        src={staticFile(`captures/${image}`)}
        width={1920}
        height={1080}
        style={{
          width: 1920,
          height: 1080,
          objectFit: "cover",
          scale: 1.11,
          filter: "blur(36px) brightness(0.36) saturate(0.78)",
        }}
      />

      <Interactive.Div
        name="Product capture"
        style={{
          position: "absolute",
          left: 64,
          top: 36,
          width: 1792,
          height: 1008,
          overflow: "hidden",
          borderRadius: 28,
          border: "1px solid rgba(255,255,255,0.17)",
          backgroundColor: "#08110f",
          boxShadow: "0 34px 110px rgba(0,0,0,0.58)",
          scale: interpolate(frame, [0, durationInFrames], [1.008, 1.03], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.22, 0.74, 0.2, 1),
          }),
          translate: interpolate(
            frame,
            [0, durationInFrames],
            [
              `${(0.5 - focusX) * 12}px ${(0.5 - focusY) * 12}px`,
              `${(0.5 - focusX) * 58}px ${(0.5 - focusY) * 42}px`,
            ],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.22, 0.74, 0.2, 1),
            },
          ),
        }}
      >
        <CanvasImage
          src={staticFile(`captures/${image}`)}
          width={1920}
          height={1080}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.20) 0%, transparent 25%, transparent 67%, rgba(0,0,0,0.22) 100%)",
          }}
        />
        {callouts.map((spec) => (
          <Callout key={spec.label} spec={spec} />
        ))}
      </Interactive.Div>

      <Interactive.Div
        name="Scene heading"
        style={{
          position: "absolute",
          left: headingLeft,
          top: 64,
          width: 810,
          padding: "20px 24px 21px",
          borderRadius: 20,
          color: "#f6fbf9",
          backgroundColor: "rgba(3,10,9,0.88)",
          border: "1px solid rgba(157,244,211,0.20)",
          boxShadow: "0 24px 70px rgba(0,0,0,0.34)",
          backdropFilter: "blur(18px)",
          opacity: interpolate(
            frame,
            [0, 18, durationInFrames - 20, durationInFrames],
            [0, 1, 1, 0],
            {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            },
          ),
          translate: interpolate(frame, [0, 18], ["0px 18px", "0px 0px"], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 24,
            color: ACCENT,
            fontSize: 16,
            fontWeight: 780,
            letterSpacing: "0.14em",
            textTransform: "uppercase",
          }}
        >
          <span>{eyebrow}</span>
          <span style={{ color: "rgba(229,245,239,0.62)", letterSpacing: "0.08em" }}>
            {timeRange}
          </span>
        </div>
        <div
          style={{
            marginTop: 10,
            fontSize: 49,
            lineHeight: 1.02,
            fontWeight: 760,
            letterSpacing: "-0.045em",
          }}
        >
          {title}
        </div>
        <div
          style={{
            marginTop: 10,
            maxWidth: 740,
            color: "rgba(230,242,238,0.78)",
            fontSize: 23,
            lineHeight: 1.3,
            letterSpacing: "-0.015em",
          }}
        >
          {detail}
        </div>
        {command ? (
          <div
            style={{
              marginTop: 14,
              padding: "10px 13px",
              borderRadius: 11,
              backgroundColor: "rgba(157,244,211,0.08)",
              border: "1px solid rgba(157,244,211,0.16)",
              color: "#caffec",
              fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
              fontSize: 18,
              lineHeight: 1.25,
            }}
          >
            {command}
          </div>
        ) : null}
      </Interactive.Div>

      {metrics.length > 0 ? (
        <Interactive.Div
          name="Scene metrics"
          style={{
            position: "absolute",
            right: titleSide === "left" ? 76 : 1034,
            top: 76,
            display: "flex",
            gap: 12,
            opacity: interpolate(frame, [10, 32], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.bezier(0.16, 1, 0.3, 1),
            }),
          }}
        >
          {metrics.map((metric) => (
            <div
              key={metric.label}
              style={{
                minWidth: 138,
                padding: "15px 17px",
                borderRadius: 18,
                backgroundColor: "rgba(3,10,9,0.88)",
                border: "1px solid rgba(157,244,211,0.18)",
                boxShadow: "0 18px 55px rgba(0,0,0,0.32)",
                backdropFilter: "blur(16px)",
              }}
            >
              <div
                style={{
                  color: "#ffffff",
                  fontSize: 39,
                  lineHeight: 1,
                  fontWeight: 780,
                  letterSpacing: "-0.04em",
                }}
              >
                {metric.value}
              </div>
              <div
                style={{
                  marginTop: 7,
                  color: "rgba(216,237,230,0.64)",
                  fontSize: 14,
                  fontWeight: 760,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                }}
              >
                {metric.label}
              </div>
            </div>
          ))}
        </Interactive.Div>
      ) : null}

      <div
        style={{
          position: "absolute",
          left: 78,
          bottom: 38,
          display: "flex",
          alignItems: "center",
          gap: 11,
          padding: "9px 13px",
          borderRadius: 999,
          backgroundColor: "rgba(3,10,9,0.80)",
          border: "1px solid rgba(255,255,255,0.12)",
          color: "rgba(235,246,242,0.72)",
          fontSize: 15,
          fontWeight: 720,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
        }}
      >
        <span style={{ color: ACCENT }}>OrgMemory</span>
        <span>WebMCP demo</span>
        <span style={{ color: "rgba(235,246,242,0.35)" }}>•</span>
        <span>{String(chapter).padStart(2, "0")} / 14</span>
      </div>
    </AbsoluteFill>
  );
};
