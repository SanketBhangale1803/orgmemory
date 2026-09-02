export const FPS = 30;
export const TOTAL_FRAMES = 5490;

export const COLORS = {
  ink: "#13090b",
  paper: "#fbf7f5",
  burgundy: "#7d1730",
  burgundyBright: "#a72949",
  mint: "#9df4d3",
  deep: "#06100e",
  softInk: "rgba(19,9,11,0.66)",
};

export const SCENES = {
  problem: { from: 0, duration: 720 },
  built: { from: 720, duration: 840 },
  briefing: { from: 1560, duration: 1860 },
  permission: { from: 3420, duration: 720 },
  loop: { from: 4140, duration: 960 },
  close: { from: 5100, duration: 390 },
} as const;
