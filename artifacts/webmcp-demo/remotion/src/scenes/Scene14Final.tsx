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

const steps = [
  "Ingest sources",
  "Extract memory",
  "Retrieve via WebMCP",
  "Approve writes",
  "Prepare work",
  "Record outcomes",
];

export const Scene14Final: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#06100e",
        color: "#f6fbf9",
        overflow: "hidden",
      }}
    >
      <CanvasImage
        src={staticFile("captures/01-command-center.png")}
        width={1920}
        height={1080}
        style={{
          width: 1920,
          height: 1080,
          objectFit: "cover",
          scale: interpolate(frame, [0, durationInFrames], [1.03, 1.08], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
          filter: "blur(15px) brightness(0.27) saturate(0.72)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 45%, rgba(18,52,43,0.44), rgba(2,8,7,0.92) 64%)",
        }}
      />

      <Interactive.Div
        name="Final title"
        style={{
          position: "absolute",
          left: 170,
          right: 170,
          top: 150,
          textAlign: "center",
          opacity: interpolate(frame, [0, 18], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }),
          translate: interpolate(frame, [0, 18], ["0px 20px", "0px 0px"], {
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
            fontWeight: 790,
            letterSpacing: "0.16em",
            textTransform: "uppercase",
          }}
        >
          Complete application loop • 02:50 — 03:00
        </div>
        <div
          style={{
            marginTop: 18,
            fontSize: 84,
            lineHeight: 0.98,
            fontWeight: 780,
            letterSpacing: "-0.055em",
          }}
        >
          OrgMemory, end to end.
        </div>
        <div
          style={{
            marginTop: 20,
            color: "rgba(228,242,237,0.72)",
            fontSize: 30,
            lineHeight: 1.28,
          }}
        >
          The same governed memory path powers every browser-agent session.
        </div>
      </Interactive.Div>

      <div
        style={{
          position: "absolute",
          left: 112,
          right: 112,
          top: 520,
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gap: 14,
        }}
      >
        {steps.map((step, index) => {
          const start = 18 + index * 8;
          const progress = spring({
            frame: frame - start,
            fps,
            config: { damping: 18, stiffness: 150, mass: 0.72 },
            durationInFrames: 24,
          });
          return (
            <Interactive.Div
              key={step}
              name={`Flow step ${index + 1}`}
              style={{
                position: "relative",
                minHeight: 142,
                padding: "23px 20px",
                borderRadius: 20,
                border: "1px solid rgba(157,244,211,0.22)",
                backgroundColor: "rgba(4,14,11,0.80)",
                boxShadow: "0 22px 70px rgba(0,0,0,0.35)",
                backdropFilter: "blur(16px)",
                opacity: progress,
                scale: interpolate(progress, [0, 1], [0.94, 1], {
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                }),
              }}
            >
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 99,
                  display: "grid",
                  placeItems: "center",
                  backgroundColor: "#9df4d3",
                  color: "#06100e",
                  fontSize: 17,
                  fontWeight: 850,
                }}
              >
                {index + 1}
              </div>
              <div
                style={{
                  marginTop: 18,
                  fontSize: 24,
                  lineHeight: 1.12,
                  fontWeight: 720,
                  letterSpacing: "-0.025em",
                }}
              >
                {step}
              </div>
              {index < steps.length - 1 ? (
                <div
                  style={{
                    position: "absolute",
                    right: -18,
                    top: 65,
                    color: "#9df4d3",
                    fontSize: 25,
                    fontWeight: 800,
                  }}
                >
                  →
                </div>
              ) : null}
            </Interactive.Div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          left: 112,
          right: 112,
          bottom: 118,
          height: 1,
          backgroundColor: "rgba(157,244,211,0.18)",
        }}
      />
    </AbsoluteFill>
  );
};
