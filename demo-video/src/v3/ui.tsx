import React from "react";
import { Img, staticFile } from "remotion";
import { c, f } from "./theme";
import { glide, lin, mix, pop, ramp } from "./time";

export type Rect = { x: number; y: number; w: number };
type Key = { at: number; rect: Rect; dur?: number };

/** A screenshot in a browser frame with a camera that glides between regions (source is 1600×900). */
export const Shot: React.FC<{
  t: number;
  src: string;
  keys: Key[];
  frame?: { x: number; y: number; w: number; h: number };
  opacity?: number;
  children?: (scale: number) => React.ReactNode;
  url?: string;
}> = ({ t, src, keys, frame = { x: 248, y: 150, w: 1424, h: 801 }, opacity = 1, children, url = "flatline · dashboard" }) => {
  let r = keys[0].rect;
  for (let i = 1; i < keys.length; i++) {
    const k = glide(t, keys[i].at, keys[i].at + (keys[i].dur ?? 1.4));
    r = { x: mix(r.x, keys[i].rect.x, k), y: mix(r.y, keys[i].rect.y, k), w: mix(r.w, keys[i].rect.w, k) };
  }
  const s = frame.w / r.w;
  const bar = 34;
  return (
    <div style={{ position: "absolute", left: frame.x, top: frame.y - bar, width: frame.w, opacity, borderRadius: 16, overflow: "hidden", boxShadow: "0 40px 120px rgba(0,0,0,.65), 0 0 0 1px rgba(255,255,255,.09)" }}>
      <div style={{ height: bar, background: "#1B2028", display: "flex", alignItems: "center", gap: 8, padding: "0 14px" }}>
        {["#3a414c", "#3a414c", "#3a414c"].map((col, i) => (
          <div key={i} style={{ width: 10, height: 10, borderRadius: 5, background: col }} />
        ))}
        <div style={{ marginLeft: 14, fontFamily: f.mono, fontSize: 14, color: c.faint }}>{url}</div>
      </div>
      <div style={{ position: "relative", width: frame.w, height: frame.h, overflow: "hidden", background: "#fff" }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 1600, height: 900, transformOrigin: "0 0", transform: `scale(${s}) translate(${-r.x}px, ${-r.y}px)` }}>
          <Img src={staticFile(`v3/${src}`)} style={{ width: 1600, height: 900, display: "block" }} />
          {children ? children(s) : null}
        </div>
      </div>
    </div>
  );
};

/** A ring around a region of the screenshot, in source pixels. Dims everything else slightly. */
export const Ring: React.FC<{ t: number; at: number; until?: number; box: [number, number, number, number]; color?: string; s: number; pad?: number }> = ({
  t,
  at,
  until = 1e9,
  box,
  color = c.warn,
  s,
  pad = 8,
}) => {
  const k = Math.min(ramp(t, at, at + 0.45), 1 - lin(t, until - 0.3, until));
  if (k <= 0) return null;
  const grow = (1 - k) * 14;
  return (
    <div
      style={{
        position: "absolute",
        left: box[0] - pad - grow,
        top: box[1] - pad - grow,
        width: box[2] + (pad + grow) * 2,
        height: box[3] + (pad + grow) * 2,
        borderRadius: 12 / s + 6,
        border: `${3.5 / s}px solid ${color}`,
        boxShadow: `0 0 0 ${2000}px rgba(8,10,14,${0.34 * k}), 0 0 ${30 / s}px ${color}88`,
        opacity: k,
      }}
    />
  );
};

/** A mouse pointer that travels to a point in source pixels and clicks. */
export const Cursor: React.FC<{ t: number; from: [number, number]; to: [number, number]; start: number; click: number; s: number }> = ({ t, from, to, start, click, s }) => {
  const k = glide(t, start, click - 0.25);
  const x = mix(from[0], to[0], k);
  const y = mix(from[1], to[1], k) - Math.sin(k * Math.PI) * 30;
  const press = 1 - 0.18 * Math.max(0, 1 - Math.abs(t - click) / 0.12);
  const ripple = lin(t, click, click + 0.6);
  if (t < start - 0.2) return null;
  return (
    <>
      {ripple > 0 && ripple < 1 ? (
        <div style={{ position: "absolute", left: to[0] - 60 * ripple, top: to[1] - 60 * ripple, width: 120 * ripple, height: 120 * ripple, borderRadius: "50%", border: `${3 / s}px solid ${c.blue}`, opacity: 1 - ripple }} />
      ) : null}
      <svg width={34 / s} height={34 / s} viewBox="0 0 24 24" style={{ position: "absolute", left: x, top: y, transform: `scale(${press})`, transformOrigin: "0 0", filter: "drop-shadow(0 2px 4px rgba(0,0,0,.5))", opacity: lin(t, start - 0.2, start) }}>
        <path d="M4 2 L4 19 L8.6 15 L11.6 22 L14.4 20.8 L11.4 14 L18 14 Z" fill="#fff" stroke="#111" strokeWidth={1.2} strokeLinejoin="round" />
      </svg>
    </>
  );
};

/** A small tag that names what the viewer is looking at. */
export const Tag: React.FC<{ t: number; at: number; until?: number; x: number; y: number; text: string; color?: string; sub?: string }> = ({ t, at, until = 1e9, x, y, text, color = c.warn, sub }) => {
  const k = Math.min(pop(t, at, 0.5), 1 - lin(t, until - 0.25, until));
  if (k <= 0) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: `scale(${0.9 + 0.1 * k})`, transformOrigin: "0 50%", opacity: Math.min(1, k * 1.4), background: c.ink, border: `2px solid ${color}`, borderRadius: 14, padding: "12px 20px", boxShadow: `0 12px 40px rgba(0,0,0,.6), 0 0 30px ${color}33` }}>
      <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 27, letterSpacing: 1.2, color, textTransform: "uppercase" }}>{text}</div>
      {sub ? <div style={{ fontFamily: f.sans, fontSize: 26, color: c.text, marginTop: 4 }}>{sub}</div> : null}
    </div>
  );
};

export const Check: React.FC<{ size?: number; color?: string }> = ({ size = 28, color = c.alive }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M5 12.5 L10 17.5 L19.5 7" fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
export const Cross: React.FC<{ size?: number; color?: string }> = ({ size = 28, color = c.flat }) => (
  <svg width={size} height={size} viewBox="0 0 24 24">
    <path d="M6 6 L18 18 M18 6 L6 18" fill="none" stroke={color} strokeWidth={3} strokeLinecap="round" />
  </svg>
);

export const money = (n: number): string => `$${n.toLocaleString("en-US")}`;
