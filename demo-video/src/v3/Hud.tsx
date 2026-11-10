import React from "react";
import { c, f } from "./theme";
import { alive, Pulse } from "./Pulse";
import { SCENES, lin, ramp } from "./time";

const STEPS: [string, string][] = [
  ["detect", "Detect"],
  ["agents", "Diagnose"],
  ["approve", "Fix"],
  ["recover", "Recover"],
];

/** The strip that stays on screen through the demo: the shop's pulse, and where we are. */
export const Hud: React.FC<{ t: number }> = ({ t }) => {
  const k = Math.min(ramp(t, SCENES.break.start, SCENES.break.start + 0.8), 1 - lin(t, SCENES.close.start - 0.5, SCENES.close.start));
  if (k <= 0) return null;
  const on = alive(t);
  const col = on ? c.alive : c.flat;
  const current = STEPS.findIndex(([id]) => t >= SCENES[id].start && t < SCENES[id].end);
  const guard = t >= SCENES.trust.start;
  return (
    <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 96, opacity: k, transform: `translateY(${(1 - k) * -30}px)`, display: "flex", alignItems: "center", padding: "0 64px", boxSizing: "border-box" }}>
      <div style={{ width: 350 }}>
        <div style={{ fontFamily: f.mono, fontSize: 17, letterSpacing: 2.4, color: c.faint }}>LUMEN COFFEE CO. · REVENUE</div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
          <div style={{ width: 10, height: 10, borderRadius: 5, background: col, boxShadow: `0 0 12px ${col}` }} />
          <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 22, letterSpacing: 1.6, color: col }}>{on ? "TAKING PAYMENTS" : "CHECKOUT DOWN"}</div>
        </div>
      </div>
      <div style={{ width: 560, height: 64, marginLeft: 10 }}>
        <Pulse t={t} width={560} height={64} seconds={5} stroke={2.6} glow={0.8} />
      </div>
      <div style={{ flex: 1 }} />
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        {STEPS.map(([id, label], i) => {
          const done = current > i || guard;
          const now = current === i;
          return (
            <React.Fragment key={id}>
              {i ? <div style={{ width: 26, height: 2, background: done || now ? c.dim : c.line }} /> : null}
              <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 19, letterSpacing: 1.4, padding: "8px 16px", borderRadius: 999, color: now ? c.ink : done ? c.dim : c.faint, background: now ? c.text : "transparent", border: `1.5px solid ${now ? c.text : done ? c.faint : c.line}` }}>
                {label.toUpperCase()}
              </div>
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
