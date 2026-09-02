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

export const ChallengeCaptions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender("Loading challenge captions"));

  const load = useCallback(async () => {
    try {
      const response = await fetch(staticFile("captions-challenge-slow.json"));
      setCaptions((await response.json()) as Caption[]);
      continueRender(handle);
    } catch (error) {
      cancelRender(error);
    }
  }, [cancelRender, continueRender, handle]);

  useEffect(() => {
    load();
  }, [load]);

  if (!captions) return null;
  const nowMs = (frame / fps) * 1000;
  const caption = captions.find((item) => nowMs >= item.startMs && nowMs < item.endMs);
  if (!caption) return null;
  const localMs = nowMs - caption.startMs;
  const durationMs = caption.endMs - caption.startMs;

  return (
    <Interactive.Div
      name="Challenge captions"
      style={{
        position: "absolute",
        left: "50%",
        bottom: 28,
        width: 1110,
        padding: "13px 21px 14px",
        borderRadius: 15,
        backgroundColor: "rgba(2,8,7,0.90)",
        border: "1px solid rgba(157,244,211,0.22)",
        boxShadow: "0 18px 60px rgba(0,0,0,0.38)",
        backdropFilter: "blur(16px)",
        color: "#f8fffc",
        fontSize: 27,
        lineHeight: 1.22,
        fontWeight: 620,
        letterSpacing: "-0.018em",
        textAlign: "center",
        opacity: interpolate(
          localMs,
          [0, 120, Math.max(121, durationMs - 140), durationMs],
          [0, 1, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        ),
        translate: interpolate(localMs, [0, 150], ["-50% 8px", "-50% 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
      }}
    >
      {caption.text.trim()}
    </Interactive.Div>
  );
};
