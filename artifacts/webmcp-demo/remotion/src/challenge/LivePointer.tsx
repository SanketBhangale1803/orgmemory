import { Easing, interpolate, useCurrentFrame } from "remotion";

type Point = { frame: number; x: number; y: number; click?: boolean };

// A deliberately restrained cursor track: it follows the visual story rather
// than constantly moving, so each stop reads as an intentional operator action.
const TRACK: Point[] = [
  { frame: 0, x: 1060, y: 430 },
  { frame: 150, x: 1045, y: 515 },
  { frame: 490, x: 1030, y: 520, click: true },
  { frame: 720, x: 1070, y: 450 },
  { frame: 1080, x: 1130, y: 745 },
  { frame: 1500, x: 1184, y: 152, click: true },
  { frame: 1690, x: 1300, y: 472 },
  { frame: 1860, x: 1567, y: 434, click: true },
  { frame: 2090, x: 523, y: 410 },
  { frame: 2470, x: 926, y: 334 },
  { frame: 2940, x: 1120, y: 510 },
  { frame: 3340, x: 1234, y: 491 },
  { frame: 3580, x: 963, y: 645, click: true },
  { frame: 3970, x: 1280, y: 472 },
  { frame: 4300, x: 948, y: 352 },
  { frame: 4810, x: 1242, y: 582, click: true },
  { frame: 5160, x: 960, y: 628 },
  { frame: 5450, x: 1000, y: 558 },
];

const getPoint = (frame: number) => {
  const after = TRACK.findIndex((point) => point.frame > frame);
  if (after === -1) return TRACK[TRACK.length - 1];
  if (after === 0) return TRACK[0];
  const a = TRACK[after - 1];
  const b = TRACK[after];
  const progress = interpolate(frame, [a.frame, b.frame], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.22, 0.76, 0.22, 1),
  });
  return { x: a.x + (b.x - a.x) * progress, y: a.y + (b.y - a.y) * progress };
};

export const LivePointer: React.FC = () => {
  const frame = useCurrentFrame();
  const point = getPoint(frame);
  const lastClick = [...TRACK].reverse().find((item) => item.click && item.frame <= frame);
  const clickAge = lastClick ? frame - lastClick.frame : 999;
  const pulse = interpolate(clickAge, [0, 3, 17], [0.2, 1, 0], {
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
        width: 58,
        height: 58,
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
            border: "3px solid rgba(157,244,211,0.92)",
            opacity: pulse,
            scale: interpolate(clickAge, [0, 17], [0.55, 1.75], {
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
