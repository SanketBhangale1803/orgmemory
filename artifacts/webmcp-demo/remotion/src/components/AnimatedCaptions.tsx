import type { Caption } from "@remotion/captions";
import { useCallback, useEffect, useState } from "react";
import {
  Easing,
  Interactive,
  interpolate,
  staticFile,
  useCurrentFrame,
  useDelayRender,
  useVideoConfig,
} from "remotion";

export const AnimatedCaptions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender("Loading captions"));

  const fetchCaptions = useCallback(async () => {
    try {
      const response = await fetch(staticFile("captions.json"));
      const data = (await response.json()) as Caption[];
      setCaptions(data);
      continueRender(handle);
    } catch (error) {
      cancelRender(error);
    }
  }, [cancelRender, continueRender, handle]);

  useEffect(() => {
    fetchCaptions();
  }, [fetchCaptions]);

  if (!captions) {
    return null;
  }

  const nowMs = (frame / fps) * 1000;
  const current = captions.find(
    (caption) => nowMs >= caption.startMs && nowMs < caption.endMs,
  );

  if (!current) {
    return null;
  }

  const localMs = nowMs - current.startMs;
  const durationMs = current.endMs - current.startMs;

  return (
    <Interactive.Div
      name="Captions"
      style={{
        position: "absolute",
        left: "50%",
        bottom: 38,
        width: 1080,
        padding: "14px 24px 15px",
        translate: interpolate(localMs, [0, 170], ["-50% 10px", "-50% 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        opacity: interpolate(
          localMs,
          [0, 150, Math.max(151, durationMs - 180), durationMs],
          [0, 1, 1, 0],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          },
        ),
        borderRadius: 16,
        backgroundColor: "rgba(2,8,7,0.90)",
        border: "1px solid rgba(157,244,211,0.18)",
        boxShadow: "0 18px 60px rgba(0,0,0,0.42)",
        backdropFilter: "blur(18px)",
        color: "#f7fbfa",
        fontSize: 29,
        lineHeight: 1.22,
        fontWeight: 610,
        textAlign: "center",
        letterSpacing: "-0.018em",
      }}
    >
      <span
        style={{
          display: "inline-block",
          width: 9,
          height: 9,
          marginRight: 13,
          borderRadius: 99,
          backgroundColor: "#9df4d3",
          boxShadow: "0 0 18px rgba(157,244,211,0.72)",
          verticalAlign: "0.12em",
        }}
      />
      {current.text.trim()}
    </Interactive.Div>
  );
};
