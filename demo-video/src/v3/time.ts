import { Easing, interpolate, useCurrentFrame } from "remotion";
import vo from "./vo.json";
import { FPS } from "./theme";

export type Line = { scene: string; id: string; start: number; end: number; text: string };
export const LINES = vo.lines as Line[];
export const TOTAL = vo.total as number;

/** When a narration line starts, in seconds. Every visual beat hangs off these. */
export const cue = (id: string): number => {
  const line = LINES.find((l) => l.id === id);
  if (!line) throw new Error(`no narration line ${id}`);
  return line.start;
};
export const cueEnd = (id: string): number => LINES.find((l) => l.id === id)!.end;

/** Scene windows in seconds. A scene starts shortly before its first line. */
const firstOf = (scene: string) => LINES.find((l) => l.scene === scene)!.start;
export const SCENES = (() => {
  const order = ["open", "title", "break", "detect", "agents", "approve", "recover", "trust", "close"];
  const lead: Record<string, number> = { open: 1.8, title: 1.5, break: 1.0, detect: 0.6, agents: 0.7, approve: 0.5, recover: 1.3, trust: 1.0, close: 1.0 };
  const starts = order.map((s) => Math.max(0, firstOf(s) - lead[s]));
  return Object.fromEntries(order.map((s, i) => [s, { start: starts[i], end: i + 1 < order.length ? starts[i + 1] : TOTAL }])) as Record<
    string,
    { start: number; end: number }
  >;
})();

/** The pulse's story: when revenue is alive and when it is flat. */
export const BREAK_OPEN = cueEnd("breaks") - 1.0; // "...and checkout breaks"
export const REWIND = SCENES.title.start; // the same Friday again, this time with Flatline
export const BREAK_DEMO = cue("break") + 3.4; // "One bad config..."
export const CLICK = cueEnd("click") + 0.45; // the approve click
export const REVIVE = CLICK + 0.35;
export const RECOVERY_CLICK = cue("after") + 6.9; // "...with one more approval"
export const PAYMENTS = [0, 0.62, 1.24, 1.86].map((d) => cueEnd("play") + 0.25 + d);

export const useT = (): number => useCurrentFrame() / FPS;

const out = Easing.bezier(0.16, 1, 0.3, 1);
const inOut = Easing.bezier(0.65, 0, 0.35, 1);

/** 0 → 1 between a and b seconds, eased out. */
export const ramp = (t: number, a: number, b: number): number =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: out });
export const glide = (t: number, a: number, b: number): number =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: inOut });
export const lin = (t: number, a: number, b: number): number =>
  interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
/** A small overshoot, for things that land. */
export const pop = (t: number, a: number, dur = 0.5): number => {
  const x = lin(t, a, a + dur);
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  return 1 + Math.exp(-6 * x) * Math.sin((x * 10 - 0.75) * ((2 * Math.PI) / 3)) * -1;
};
/** Visible between a and b with soft edges. */
export const window = (t: number, a: number, b: number, edge = 0.35): number => Math.min(ramp(t, a, a + edge), 1 - lin(t, b - edge, b));
export const mix = (a: number, b: number, k: number): number => a + (b - a) * k;
