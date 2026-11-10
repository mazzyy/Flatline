import React from "react";
import { c } from "./theme";
import { BREAK_DEMO, BREAK_OPEN, PAYMENTS, REVIVE, REWIND } from "./time";

const PERIOD = 0.92;

/** One heartbeat, phase 0..1: a small P wave, the QRS spike, a T wave. Up is positive. */
const beat = (p: number): number => {
  const g = (x: number, m: number, s: number, a: number) => a * Math.exp(-((x - m) ** 2) / (2 * s * s));
  return g(p, 0.18, 0.035, 0.1) - g(p, 0.3, 0.012, 0.14) + g(p, 0.33, 0.014, 1) - g(p, 0.365, 0.014, 0.26) + g(p, 0.58, 0.06, 0.2);
};

/** Is the shop taking money at time s? */
export const alive = (s: number): boolean => (s < BREAK_OPEN ? true : s < REWIND ? false : s < BREAK_DEMO ? true : s >= REVIVE);

/** How tall the beat is at time s: full when alive, dying over ~1.6 s at a break, taller when a payment lands. */
const strength = (s: number): number => {
  let k = 1;
  for (const [from, to] of [
    [BREAK_OPEN, REWIND],
    [BREAK_DEMO, REVIVE],
  ]) {
    if (s >= from && s < to) k = Math.max(0, 0.45 - (s - from) / 1.6) * (s - from < 1.6 ? 1 : 0);
  }
  for (const p of PAYMENTS) if (s >= p - 0.3 && s < p + 0.62) k = Math.max(k, 1.55);
  return k;
};

const phaseOrigin = (s: number): number => (s >= REVIVE ? REVIVE - 0.33 * PERIOD + 0.05 : s >= REWIND ? REWIND + 0.4 : 0.35);

export const signal = (s: number): number => {
  if (s < 0) return 0;
  const o = phaseOrigin(s);
  // After a payment the next spike is anchored to it, so the beat lands with the money.
  for (const p of PAYMENTS) if (s >= p - 0.3 && s < p + 0.62) return strength(s) * beat((s - p + 0.33 * 0.62) / 0.62);
  const ph = (((s - o) % PERIOD) + PERIOD) % PERIOD;
  return strength(s) * beat(ph / PERIOD);
};

/**
 * The revenue monitor: a scrolling trace whose right edge is "now".
 * Green while the shop takes money, red and flat while it does not.
 */
export const Pulse: React.FC<{
  t: number;
  width: number;
  height: number;
  seconds?: number; // how much history fits across the width
  stroke?: number;
  glow?: number;
  head?: boolean;
}> = ({ t, width, height, seconds = 6, stroke = 4, glow = 1, head = true }) => {
  const n = Math.round(width / 3);
  const mid = height * 0.62;
  const amp = height * 0.56;
  const pts: string[] = [];
  const stops: { x: number; on: boolean }[] = [];
  let last: boolean | null = null;
  for (let i = 0; i <= n; i++) {
    const x = (i / n) * width;
    const s = t - ((width - x) / width) * seconds;
    const on = s < 0 ? true : alive(s);
    if (on !== last) {
      stops.push({ x, on });
      last = on;
    }
    pts.push(`${x.toFixed(1)},${(mid - signal(s) * amp).toFixed(1)}`);
  }
  const id = `pg-${Math.round(width)}-${Math.round(height)}`;
  const nowOn = alive(t);
  const col = nowOn ? c.alive : c.flat;
  const hy = mid - signal(t) * amp;
  return (
    <svg width={width} height={height} style={{ overflow: "visible", display: "block" }}>
      <defs>
        <linearGradient id={id} gradientUnits="userSpaceOnUse" x1={0} x2={width} y1={0} y2={0}>
          <stop offset={0} stopColor={stops[0].on ? c.alive : c.flat} stopOpacity={0} />
          <stop offset={0.12} stopColor={stops[0].on ? c.alive : c.flat} stopOpacity={0.9} />
          {stops.slice(1).flatMap((s, i) => [
            <stop key={`a${i}`} offset={s.x / width} stopColor={s.on ? c.flat : c.alive} />,
            <stop key={`b${i}`} offset={s.x / width} stopColor={s.on ? c.alive : c.flat} />,
          ])}
          <stop offset={1} stopColor={col} />
        </linearGradient>
        <filter id={`${id}-blur`} x="-10%" y="-200%" width="120%" height="500%">
          <feGaussianBlur stdDeviation={stroke * 2.2} />
        </filter>
      </defs>
      <polyline points={pts.join(" ")} fill="none" stroke={`url(#${id})`} strokeWidth={stroke * 2.4} strokeLinejoin="round" opacity={0.42 * glow} filter={`url(#${id}-blur)`} />
      <polyline points={pts.join(" ")} fill="none" stroke={`url(#${id})`} strokeWidth={stroke} strokeLinejoin="round" strokeLinecap="round" />
      {head ? (
        <>
          <circle cx={width} cy={hy} r={stroke * 3.2} fill={col} opacity={0.25} />
          <circle cx={width} cy={hy} r={stroke * 1.3} fill={col} />
        </>
      ) : null}
    </svg>
  );
};
