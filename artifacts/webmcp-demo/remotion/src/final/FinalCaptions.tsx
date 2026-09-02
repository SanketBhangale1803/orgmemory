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

export const FinalCaptions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender("Loading final captions"));

  const load = useCallback(async () => {
    try {
      const response = await fetch(staticFile("captions-final.json"));
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
      name="Burned-in captions"
      style={{
        position: "absolute",
        left: "50%",
        bottom: 30,
        width: 1220,
        padding: "13px 22px 15px",
        borderRadius: 15,
        backgroundColor: "rgba(2,8,7,0.91)",
        border: "1px solid rgba(157,244,211,0.25)",
        boxShadow: "0 20px 62px rgba(0,0,0,0.36)",
        color: "#f8fffc",
        fontFamily: '"OrgMemory Sans", Arial, sans-serif',
        fontSize: 28,
        lineHeight: 1.22,
        fontWeight: 640,
        letterSpacing: "-0.015em",
        textAlign: "center",
        opacity: interpolate(
          localMs,
          [0, 110, Math.max(111, durationMs - 120), durationMs],
          [0, 1, 1, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
        ),
        translate: interpolate(localMs, [0, 140], ["-50% 7px", "-50% 0px"], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        }),
        zIndex: 110,
      }}
    >
      {caption.text.trim()}
    </Interactive.Div>
  );
};
