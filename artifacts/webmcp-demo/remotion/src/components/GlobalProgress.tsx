import {
  Easing,
  Interactive,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export const GlobalProgress: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  return (
    <Interactive.Div
      name="Video progress"
      style={{
        position: "absolute",
        left: 0,
        bottom: 0,
        width: interpolate(frame, [0, durationInFrames - 1], [0, 1920], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.linear,
        }),
        height: 6,
        backgroundColor: "#9df4d3",
        boxShadow: "0 -4px 20px rgba(157,244,211,0.38)",
      }}
    />
  );
};
