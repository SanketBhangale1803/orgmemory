export type CalloutSpec = {
  x: number;
  y: number;
  width: number;
  height: number;
  label: string;
  enterAt?: number;
};

export type MetricSpec = {
  value: string;
  label: string;
};

export type ScreenshotSceneProps = {
  image: string;
  eyebrow: string;
  title: string;
  detail: string;
  timeRange: string;
  chapter: number;
  focusX?: number;
  focusY?: number;
  titleSide?: "left" | "right";
  command?: string;
  callouts?: CalloutSpec[];
  metrics?: MetricSpec[];
};
