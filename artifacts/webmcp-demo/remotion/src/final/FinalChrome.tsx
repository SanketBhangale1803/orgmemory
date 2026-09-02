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
import { FINAL_COLORS } from "./constants";

export const FinalSceneShell: React.FC<{
  route: "/" | "/webmcp" | "/approvals" | "/loop";
  children: React.ReactNode;
  dark?: boolean;
  label?: string;
}> = ({ route, children, dark = false, label }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundColor: dark ? FINAL_COLORS.deep : FINAL_COLORS.paper,
        color: dark ? "#f5fffb" : FINAL_COLORS.ink,
        fontFamily: '"OrgMemory Sans", Arial, sans-serif',
        opacity,
      }}
    >
      {children}
      <Interactive.Div
        name="Current route"
        style={{
          position: "absolute",
          left: 58,
          top: 44,
          display: "flex",
          alignItems: "center",
          gap: 14,
          padding: "10px 15px",
          borderRadius: 999,
          backgroundColor: dark ? "rgba(2,8,7,0.82)" : "rgba(255,255,255,0.90)",
          border: dark
            ? "1px solid rgba(157,244,211,0.22)"
            : "1px solid rgba(125,23,48,0.14)",
          boxShadow: "0 14px 44px rgba(0,0,0,0.12)",
          color: dark ? "#eafff6" : "#4b101e",
          fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
          fontSize: 16,
          fontWeight: 760,
          zIndex: 60,
        }}
      >
        <span style={{ color: dark ? FINAL_COLORS.mint : FINAL_COLORS.burgundyBright }}>●</span>
        <span>orgmemory.vercel.app{route}</span>
        {label ? (
          <span
            style={{
              marginLeft: 3,
              paddingLeft: 14,
              borderLeft: dark
                ? "1px solid rgba(157,244,211,0.20)"
                : "1px solid rgba(125,23,48,0.16)",
              fontFamily: '"OrgMemory Sans", Arial, sans-serif',
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {label}
          </span>
        ) : null}
      </Interactive.Div>
    </AbsoluteFill>
  );
};

export const FinalCapture: React.FC<{
  image: string;
  path?: "captures" | "captures/live";
  brightness?: number;
  blur?: number;
  fromScale?: number;
  toScale?: number;
  position?: string;
}> = ({
  image,
  path = "captures",
  brightness = 1,
  blur = 0,
  fromScale = 1.0,
  toScale = 1.03,
  position = "center",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <CanvasImage
      src={staticFile(`${path}/${image}`)}
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

export const ToolNameChip: React.FC<{
  name: string;
  tone?: "mint" | "burgundy";
}> = ({ name, tone = "mint" }) => (
  <Interactive.Div
    name={`Tool ${name}`}
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 10,
      padding: "10px 14px",
      borderRadius: 999,
      backgroundColor: tone === "mint" ? "rgba(157,244,211,0.10)" : "rgba(125,23,48,0.10)",
      border: tone === "mint"
        ? "1px solid rgba(157,244,211,0.34)"
        : "1px solid rgba(125,23,48,0.28)",
      color: tone === "mint" ? FINAL_COLORS.mint : FINAL_COLORS.burgundy,
      fontFamily: "SFMono-Regular, Menlo, Consolas, monospace",
      fontSize: 19,
      fontWeight: 820,
      letterSpacing: "-0.02em",
    }}
  >
    <span style={{ fontSize: 13 }}>●</span>
    {name}
  </Interactive.Div>
);
