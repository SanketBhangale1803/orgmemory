import type { Caption } from "@remotion/captions";
import { useEffect, useState } from "react";
import { Easing, interpolate, staticFile, useCurrentFrame, useDelayRender, useVideoConfig } from "remotion";

export const LiveCaptions: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const [captions, setCaptions] = useState<Caption[] | null>(null);
  const { delayRender, continueRender, cancelRender } = useDelayRender();
  const [handle] = useState(() => delayRender("Loading live demo captions"));

  useEffect(() => {
    fetch(staticFile("captions-live.json"))
      .then((response) => response.json())
      .then((items) => {
        setCaptions(items as Caption[]);
        continueRender(handle);
      })
      .catch(cancelRender);
  }, [cancelRender, continueRender, handle]);

  if (!captions) return null;
  const now = (frame / fps) * 1000;
  const caption = captions.find((item) => now >= item.startMs && now < item.endMs);
  if (!caption) return null;
  const local = now - caption.startMs;
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        bottom: 63,
        width: 1260,
        padding: "13px 22px 15px",
        borderRadius: 15,
        backgroundColor: "rgba(7,17,15,0.92)",
        border: "1px solid rgba(157,244,211,0.24)",
        boxShadow: "0 18px 60px rgba(0,0,0,0.30)",
        color: "#f7fffb",
        fontFamily: '"OrgMemory Sans", Arial, sans-serif',
        fontSize: 28,
        lineHeight: 1.25,
        fontWeight: 650,
        textAlign: "center",
        opacity: interpolate(local, [0, 120], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        translate: interpolate(local, [0, 160], ["-50% 8px", "-50% 0px"], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }),
      }}
    >
      {caption.text.trim()}
    </div>
  );
};
