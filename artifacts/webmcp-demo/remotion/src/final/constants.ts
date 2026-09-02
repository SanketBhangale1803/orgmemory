export const FINAL_FPS = 30;
export const FINAL_TOTAL_FRAMES = 5100;

export const FINAL_SCENES = {
  intro: { from: 0, duration: 810 },
  surface: { from: 810, duration: 570 },
  briefing: { from: 1380, duration: 1320 },
  boundary: { from: 2700, duration: 660 },
  approvals: { from: 3360, duration: 600 },
  loop: { from: 3960, duration: 660 },
  close: { from: 4620, duration: 480 },
} as const;

export const FINAL_COLORS = {
  paper: "#fbf7f5",
  ink: "#170b0e",
  burgundy: "#7d1730",
  burgundyBright: "#a72949",
  deep: "#06100e",
  mint: "#9df4d3",
  green: "#174f3c",
};
