import React from "react";
import { c, f } from "../theme";
import { Pulse } from "../Pulse";
import { SCENES, cue, lin, pop, ramp } from "../time";

/** The same Friday, with someone on call. */
export const Title: React.FC<{ t: number }> = ({ t }) => {
  const a = SCENES.title.start + 1.5;
  const b = SCENES.break.start + 0.5;
  if (t < a - 0.1 || t > b) return null;
  const k = pop(t, a, 0.7);
  const out = 1 - lin(t, b - 0.6, b);
  return (
    <div style={{ position: "absolute", inset: 0, opacity: out }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 250, textAlign: "center" }}>
        <div style={{ fontFamily: f.mono, fontSize: 24, letterSpacing: 6, color: c.alive, opacity: ramp(t, a + 0.1, a + 0.7) }}>SAME FRIDAY. THIS TIME, SOMEONE IS ON CALL.</div>
        <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 250, letterSpacing: -10, color: c.text, lineHeight: 1, marginTop: 26, opacity: Math.min(1, k * 1.3), transform: `scale(${0.94 + 0.06 * k})` }}>Flatline</div>
      </div>
      <div style={{ position: "absolute", left: 0, top: 590, opacity: ramp(t, a, a + 0.6) }}>
        <Pulse t={t} width={1920} height={170} seconds={7} stroke={4} head={false} />
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 800, textAlign: "center", fontFamily: f.serif, fontStyle: "italic", fontSize: 62, color: c.text, opacity: ramp(t, cue("built") + 2.2, cue("built") + 2.9), transform: `translateY(${(1 - ramp(t, cue("built") + 2.2, cue("built") + 3)) * 18}px)` }}>
        An on-call engineer for your PayPal revenue.
      </div>
    </div>
  );
};
