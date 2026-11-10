import React from "react";
import { c, f } from "../theme";
import { SCENES, cue, lin, mix, pop, ramp, window as win } from "../time";
import { Ring, Shot } from "../ui";

/** Why you can let it near money: agents ask, code decides, and a benchmark attacks it. */
export const Trust: React.FC<{ t: number }> = ({ t }) => {
  const S = SCENES.trust;
  if (t < S.start || t > SCENES.close.start + 0.5) return null;
  const refusedAt = cue("refused") - 0.3;
  const tiersAt = cue("tiers") - 0.3;
  const benchAt = cue("bench") - 0.3;
  const stamp = pop(t, cue("refused") + 2.55, 0.35);
  const BOXES: [string, string, string, string][] = [
    ["AI agents", "can only ask", "read-only access to PayPal", c.blue],
    ["Policy", "decides", "plain code, not a prompt", c.text],
    ["Executor", "the only writer", "runs what the policy allowed", c.alive],
  ];
  const TIERS: [string, string, string[], string, number][] = [
    ["AUTO", "runs on its own", ["Warning banner", "Alert the merchant", "Payment reminder"], c.blue, 0.1],
    ["APPROVAL", "waits for a human", ["Config rollback", "Recovery invoices", "A refund up to $50"], c.warn, 2.3],
    ["FORBIDDEN", "refused, always", ["Bulk refunds", "Payouts", "Anything not on the list"], c.flat, 4.0],
  ];
  const budget = ramp(t, cue("tiers") + 5.3, cue("tiers") + 6.6);
  const lit = Math.floor(mix(0, 34, lin(t, cue("bench") + 1.2, cue("bench") + 4.9)));
  return (
    <>
      {t < refusedAt + 0.4 ? (
        <div style={{ position: "absolute", inset: 0, opacity: win(t, S.start + 0.4, refusedAt + 0.3, 0.4) }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 215, textAlign: "center", fontFamily: f.serif, fontStyle: "italic", fontSize: 88, color: c.text }}>
            The agents can only ask. <span style={{ color: c.alive, opacity: ramp(t, cue("rule") + 3.3, cue("rule") + 3.8) }}>Code decides.</span>
          </div>
          <div style={{ position: "absolute", left: 0, right: 0, top: 440, display: "flex", justifyContent: "center", alignItems: "center", gap: 0 }}>
            {BOXES.map(([name, verb, sub, col], i) => {
              const k = pop(t, cue("rule") + 0.5 + i * 1.1, 0.5);
              return (
                <React.Fragment key={name}>
                  {i ? (
                    <svg width={110} height={40} style={{ opacity: k }}>
                      <path d="M10 20 H92 M78 8 L94 20 L78 32" fill="none" stroke={c.faint} strokeWidth={3.5} strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : null}
                  <div style={{ width: 440, boxSizing: "border-box", opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 26}px)`, background: c.panel, border: `2px solid ${col}77`, borderRadius: 22, padding: "30px 32px" }}>
                    <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 54, color: c.text, letterSpacing: -1.5 }}>{name}</div>
                    <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 44, color: col, marginTop: 2 }}>{verb}</div>
                    <div style={{ fontFamily: f.mono, fontSize: 19, color: c.faint, marginTop: 18 }}>{sub}</div>
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      ) : null}

      <Shot t={t} src="refused.jpg" opacity={win(t, refusedAt, tiersAt + 0.2, 0.35)} keys={[{ at: 0, rect: { x: 180, y: 203, w: 1240 } }, { at: refusedAt + 0.2, rect: { x: 200, y: 480, w: 840 }, dur: 2.2 }]}>
        {(s) => <Ring t={t} at={cue("refused") + 1.1} box={[224, 693, 1152, 112]} color={c.flat} s={s} />}
      </Shot>
      {stamp > 0 && t < tiersAt + 0.2 ? (
        <div style={{ position: "absolute", left: 1090, top: 420, opacity: Math.min(1, stamp * 2) * (1 - lin(t, tiersAt - 0.1, tiersAt + 0.2)), transform: `scale(${mix(2.2, 1, Math.min(1, stamp))}) rotate(-8deg)`, border: `7px solid ${c.flat}`, borderRadius: 18, padding: "10px 34px", fontFamily: f.mono, fontWeight: 600, fontSize: 96, letterSpacing: 10, color: c.flat, background: "rgba(7,9,12,.82)", boxShadow: `0 0 80px ${c.flat}55` }}>
          REFUSED
        </div>
      ) : null}

      {t >= tiersAt && t < benchAt + 0.4 ? (
        <div style={{ position: "absolute", inset: 0, opacity: win(t, tiersAt + 0.2, benchAt + 0.3, 0.4) }}>
          <div style={{ position: "absolute", left: 130, right: 130, top: 225, display: "flex", gap: 28 }}>
            {TIERS.map(([name, sub, items, col, dt]) => {
              const k = pop(t, cue("tiers") + dt, 0.5);
              return (
                <div key={name} style={{ flex: 1, opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 26}px)`, background: c.panel, borderTop: `6px solid ${col}`, borderRadius: 20, padding: "28px 32px 30px" }}>
                  <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 30, letterSpacing: 5, color: col }}>{name}</div>
                  <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 50, color: c.text, marginTop: 4 }}>{sub}</div>
                  <div style={{ marginTop: 22 }}>
                    {items.map((it) => (
                      <div key={it} style={{ fontFamily: f.sans, fontSize: 30, color: c.dim, padding: "9px 0", borderTop: `1px solid ${c.line}` }}>{it}</div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ position: "absolute", left: 130, right: 130, top: 770, opacity: ramp(t, cue("tiers") + 5.0, cue("tiers") + 5.5) }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontFamily: f.mono, fontSize: 24, letterSpacing: 3, color: c.dim }}>
              <span>DAILY REFUND BUDGET</span>
              <span>
                ${Math.round(180 * budget)} OF $200 · <span style={{ color: c.flat, opacity: lin(t, cue("tiers") + 6.6, cue("tiers") + 6.9) }}>NEXT $45 REFUND: BLOCKED</span>
              </span>
            </div>
            <div style={{ position: "relative", height: 26, borderRadius: 13, background: c.panel2, marginTop: 14, overflow: "hidden" }}>
              <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${90 * budget}%`, background: c.warn, borderRadius: 13 }} />
              <div style={{ position: "absolute", left: "90%", top: 0, bottom: 0, width: "22.5%", background: `repeating-linear-gradient(135deg, ${c.flat}, ${c.flat} 8px, transparent 8px, transparent 16px)`, opacity: lin(t, cue("tiers") + 6.6, cue("tiers") + 6.9) }} />
            </div>
          </div>
        </div>
      ) : null}

      {t >= benchAt ? (
        <div style={{ position: "absolute", inset: 0, opacity: win(t, benchAt + 0.2, SCENES.close.start + 0.4, 0.4) }}>
          <div style={{ position: "absolute", left: 150, top: 210 }}>
            <div style={{ fontFamily: f.mono, fontSize: 24, letterSpacing: 5, color: c.faint }}>make bench</div>
            <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 250, letterSpacing: -10, lineHeight: 1, color: lit === 34 ? c.alive : c.text, fontVariantNumeric: "tabular-nums", marginTop: 8 }}>
              {lit}
              <span style={{ color: c.faint }}>/34</span>
            </div>
            <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 50, color: c.dim, marginTop: 6 }}>checks passed</div>
          </div>
          <div style={{ position: "absolute", left: 1010, top: 236, width: 760 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(9, 1fr)", gap: 12 }}>
              {Array.from({ length: 34 }).map((_, i) => (
                <div key={i} style={{ height: 66, borderRadius: 12, background: i < lit ? c.alive : c.panel2, opacity: i < lit ? 1 : 0.7, boxShadow: i === lit - 1 ? `0 0 30px ${c.alive}` : "none" }} />
              ))}
            </div>
            <div style={{ fontFamily: f.sans, fontSize: 27, lineHeight: 1.45, color: c.dim, marginTop: 30 }}>
              5 incidents · 2 quiet days that must not alarm · 7 attacks on the policy
            </div>
            <div style={{ fontFamily: f.mono, fontSize: 20, lineHeight: 1.5, color: c.dim, marginTop: 14 }}>
              This run uses stand-in models: it proves the pipeline, the policy and the recovery maths. make bench-live scores real models.
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};
