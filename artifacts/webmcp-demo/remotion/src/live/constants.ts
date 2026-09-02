export const LIVE_FPS = 30;
export const LIVE_TOTAL_FRAMES = 4860;

export const LIVE_SCENES = {
  intro: { from: 0, duration: 840 },
  surface: { from: 840, duration: 450 },
  query: { from: 1290, duration: 450 },
  result: { from: 1740, duration: 600 },
  reconcile: { from: 2340, duration: 600 },
  gate: { from: 2940, duration: 600 },
  approvals: { from: 3540, duration: 270 },
  loop: { from: 3810, duration: 720 },
  close: { from: 4530, duration: 330 },
} as const;

export const LIVE_COLORS = {
  ink: "#170b0e",
  paper: "#fbf7f5",
  burgundy: "#8e233b",
  burgundyDark: "#4f1020",
  mint: "#9df4d3",
  deep: "#07110f",
};
