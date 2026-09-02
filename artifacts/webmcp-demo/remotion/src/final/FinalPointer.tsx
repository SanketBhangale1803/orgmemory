import { Easing, interpolate, useCurrentFrame } from "remotion";

type PointerStop = { frame: number; x: number; y: number; click?: boolean };

const STOPS: PointerStop[] = [
  { frame: 0, x: 1020, y: 500 },
  { frame: 520, x: 1260, y: 764, click: true },
  { frame: 810, x: 1148, y: 704 },
  { frame: 1240, x: 1428, y: 716 },
  { frame: 1500, x: 1238, y: 286, click: true },
  { frame: 1860, x: 464, y: 542 },
  { frame: 2220, x: 1310, y: 510, click: true },
  { frame: 2820, x: 1150, y: 360 },
  { frame: 3180, x: 1090, y: 722 },
  { frame: 3510, x: 1370, y: 526, click: true },
  { frame: 4110, x: 1488, y: 418 },
  { frame: 4380, x: 1398, y: 724, click: true },
  { frame: 4740, x: 960, y: 590 },
  { frame: 5070, x: 960, y: 590 },
];

const positionAt = (frame: number) => {
  const nextIndex = STOPS.findIndex((stop) => stop.frame > frame);
  if (nextIndex <= 0) return STOPS[Math.max(0, nextIndex)];
  if (nextIndex === -1) return STOPS[STOPS.length - 1];
  const from = STOPS[nextIndex - 1];
  const to = STOPS[nextIndex];
  const progress = interpolate(frame, [from.frame, to.frame], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.22, 0.76, 0.22, 1),
  });
  return {
    x: from.x + (to.x - from.x) * progress,
    y: from.y + (to.y - from.y) * progress,
  };
};

export const FinalPointer: React.FC = () => {
  const frame = useCurrentFrame();
  const point = positionAt(frame);
  const lastClick = [...STOPS].reverse().find((stop) => stop.click && stop.frame <= frame);
  const clickAge = lastClick ? frame - lastClick.frame : 999;
  const pulse = interpolate(clickAge, [0, 3, 18], [0.2, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      aria-hidden
      style={{
        position: "absolute",
        left: point.x,
        top: point.y,
        width: 56,
        height: 56,
        zIndex: 100,
        pointerEvents: "none",
      }}
    >
      {pulse > 0 ? (
        <div
          style={{
            position: "absolute",
            left: -16,
            top: -16,
            width: 52,
            height: 52,
            borderRadius: "50%",
            border: "3px solid rgba(157,244,211,0.94)",
            opacity: pulse,
            scale: interpolate(clickAge, [0, 18], [0.55, 1.8], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
          }}
        />
      ) : null}
      <svg viewBox="0 0 34 46" width="34" height="46" style={{ filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.5))" }}>
        <path d="M4 2.4v34.1l9.2-8.1 5.1 12.6 5.1-2.1-5.1-12.4h11.1L4 2.4Z" fill="#fff" stroke="#101010" strokeWidth="2.8" strokeLinejoin="round" />
      </svg>
    </div>
  );
};
