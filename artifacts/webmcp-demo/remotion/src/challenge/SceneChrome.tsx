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

export const sceneOpacity = (frame: number, durationInFrames: number) =>
  interpolate(
    frame,
    [0, 14, durationInFrames - 14, durationInFrames],
    [0, 1, 1, 0],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    },
  );

export const CaptureBackground: React.FC<{
  image: string;
  brightness?: number;
  blur?: number;
  fromScale?: number;
  toScale?: number;
  position?: string;
}> = ({
  image,
  brightness = 1,
  blur = 0,
  fromScale = 1.01,
  toScale = 1.045,
  position = "center",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  return (
    <CanvasImage
      src={staticFile(`captures/${image}`)}
      width={1920}
      height={1080}
      style={{
        width: 1920,
        height: 1080,
        objectFit: "cover",
        objectPosition: position,
        scale: interpolate(frame, [0, durationInFrames], [fromScale, toScale], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.22, 0.74, 0.2, 1),
        }),
        filter: `blur(${blur}px) brightness(${brightness})`,
      }}
    />
  );
};

export const SceneLabel: React.FC<{
  index: string;
  label: string;
  dark?: boolean;
}> = ({ index, label, dark = false }) => (
  <Interactive.Div
    name="Scene label"
    style={{
      position: "absolute",
      left: 72,
      top: 54,
      display: "flex",
      alignItems: "center",
      gap: 14,
      padding: "11px 16px",
      borderRadius: 999,
      backgroundColor: dark ? "rgba(2,8,7,0.82)" : "rgba(255,255,255,0.84)",
      border: dark
        ? "1px solid rgba(157,244,211,0.22)"
        : "1px solid rgba(125,23,48,0.16)",
      boxShadow: "0 12px 40px rgba(0,0,0,0.10)",
      color: dark ? "#e9fff6" : "#4b101e",
      fontSize: 16,
      fontWeight: 780,
      letterSpacing: "0.12em",
      textTransform: "uppercase",
    }}
  >
    <span style={{ color: dark ? "#9df4d3" : "#a72949" }}>{index}</span>
    <span>{label}</span>
  </Interactive.Div>
);

export const SceneShell: React.FC<{
  children: React.ReactNode;
  backgroundColor?: string;
}> = ({ children, backgroundColor = "#06100e" }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundColor,
        opacity: sceneOpacity(frame, durationInFrames),
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
