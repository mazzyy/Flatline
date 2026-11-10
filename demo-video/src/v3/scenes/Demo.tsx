import React from "react";
import { c, f } from "../theme";
import { BREAK_DEMO, CLICK, REVIVE, SCENES, cue, lin, pop, window as win } from "../time";
import { Check, Cross, Cursor, Ring, Shot, Tag } from "../ui";

const fade = (t: number, a: number, b: number, e = 0.4) => win(t, a, b, e);

/** Break → Detect → Diagnose → Fix: the incident, on the real dashboard. */
export const Demo: React.FC<{ t: number }> = ({ t }) => {
  const S = SCENES;
  if (t < S.break.start || t > S.recover.start + 0.6) return null;
  const shopAt = BREAK_DEMO + 0.35;
  const mcpAt = cue("agents") + 3.4;
  const causeAt = cue("cause") - 0.3;
  const waitsAt = cue("waits") + 2.3;
  const backAt = REVIVE + 0.9;
  const AGENTS: [string, string, string][] = [
    ["Triage", "how bad, how much", "gemini-2.5-flash-lite"],
    ["Diagnostician", "why, with evidence", "gemini-2.5-flash"],
    ["Remediator", "what to do", "gemini-2.5-flash"],
    ["Verifier", "did it work", "gemini-2.5-flash-lite"],
  ];
  const HYP: [string, boolean, number][] = [
    ["The customer's bank", false, 2.9],
    ["PayPal", false, 3.75],
    ["Our own config change", true, 4.6],
  ];
  return (
    <>
      {/* Break: one bad config */}
      <Shot t={t} src="chaos.jpg" url="flatline · chaos panel (test controls)" opacity={fade(t, S.break.start + 0.3, shopAt + 0.1)} keys={[{ at: 0, rect: { x: 180, y: 120, w: 1240 } }, { at: cue("break") + 1.2, rect: { x: 760, y: 150, w: 760 }, dur: 1.8 }]}>
        {(s) => (
          <>
            <Ring t={t} at={cue("break") + 2.2} box={[1005, 221, 368, 168]} color={c.flat} s={s} />
            <Cursor t={t} from={[1300, 560]} to={[1069, 349]} start={cue("break") + 1.6} click={BREAK_DEMO - 0.12} s={s} />
          </>
        )}
      </Shot>
      <Shot t={t} src="shop-failing.jpg" url="lumencoffee.shop/checkout" opacity={fade(t, shopAt, S.detect.start + 0.35)} keys={[{ at: 0, rect: { x: 300, y: 62, w: 1000 } }, { at: shopAt, rect: { x: 300, y: 62, w: 760 }, dur: 3 }]}>
        {(s) => <Ring t={t} at={shopAt + 0.5} box={[352, 240, 118, 30]} color={c.flat} s={s} />}
      </Shot>
      <Tag t={t} at={shopAt + 0.7} until={S.detect.start + 0.2} x={1130} y={520} text="Euros, on a US shop" sub="Every payment now fails" color={c.flat} />

      {/* Detect */}
      <Shot t={t} src="overview-incident.jpg" opacity={fade(t, S.detect.start + 0.2, S.agents.start + 0.3)} keys={[{ at: 0, rect: { x: 190, y: 150, w: 1220 } }, { at: cue("detect") + 3.4, rect: { x: 400, y: 150, w: 860 }, dur: 1.6 }]}>
        {(s) => (
          <>
            <Ring t={t} at={cue("detect") + 1.6} until={cue("detect") + 3.6} box={[224, 628, 372, 126]} color={c.flat} s={s} />
            <Ring t={t} at={cue("detect") + 4.6} box={[614, 218, 372, 129]} color={c.warn} s={s} />
          </>
        )}
      </Shot>
      <Tag t={t} at={cue("detect") + 5.2} until={S.agents.start + 0.1} x={1120} y={560} text="$108 an hour" sub="at risk, and counting" color={c.warn} />

      {/* Diagnose: the four agents */}
      {t >= S.agents.start && t < mcpAt + 0.5 ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 300, display: "flex", justifyContent: "center", gap: 26, opacity: fade(t, S.agents.start + 0.3, mcpAt + 0.4) }}>
          {AGENTS.map(([name, job, model], i) => {
            const at = cue("agents") + 0.2 + i * 0.5;
            const k = pop(t, at, 0.5);
            const lit = t > at + 0.1;
            return (
              <div key={name} style={{ width: 400, opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 30}px)`, background: c.panel, border: `2px solid ${lit && i === 1 && t > cue("agents") + 2.4 ? c.blue : c.line}`, borderRadius: 20, padding: "30px 28px", boxShadow: i === 1 && t > cue("agents") + 2.4 ? `0 0 60px ${c.blue}44` : "none" }}>
                <div style={{ fontFamily: f.mono, fontSize: 20, color: c.faint, letterSpacing: 2 }}>AGENT {i + 1}</div>
                <div style={{ fontFamily: f.sans, fontWeight: 700, fontSize: 44, color: c.text, marginTop: 8, letterSpacing: -1 }}>{name}</div>
                <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 34, color: c.dim, marginTop: 6 }}>{job}</div>
                <div style={{ fontFamily: f.mono, fontSize: 18, color: c.faint, marginTop: 22 }}>{model}</div>
                <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 18, color: c.blue, marginTop: 10, letterSpacing: 1.5 }}>READ ONLY</div>
              </div>
            );
          })}
        </div>
      ) : null}
      <Shot t={t} src="timeline.jpg" opacity={fade(t, mcpAt, causeAt + 0.2)} keys={[{ at: 0, rect: { x: 140, y: 380, w: 900 } }, { at: mcpAt, rect: { x: 210, y: 590, w: 540 }, dur: 2.2 }]}>
        {(s) => <Ring t={t} at={mcpAt + 1.4} box={[250, 742, 460, 26]} color={c.blue} s={s} pad={6} />}
      </Shot>
      <Tag t={t} at={mcpAt + 1.9} until={causeAt + 0.1} x={1010} y={770} text="PayPal MCP server" sub="A real read from the PayPal sandbox" color={c.blue} />

      <Shot t={t} src="rootcause.jpg" opacity={fade(t, causeAt + 0.1, S.approve.start + 0.3)} keys={[{ at: 0, rect: { x: 190, y: 120, w: 1220 } }, { at: causeAt + 0.3, rect: { x: 200, y: 200, w: 1010 }, dur: 5 }]}>
        {(s) => <Ring t={t} at={cue("cause") + 0.9} box={[224, 232, 1152, 360]} color={c.blue} s={s} />}
      </Shot>
      <div style={{ position: "absolute", right: 300, top: 690, display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-end" }}>
        {HYP.map(([text, ok, dt]) => {
          const at = cue("cause") + dt;
          const k = Math.min(pop(t, at, 0.45), 1 - lin(t, S.approve.start, S.approve.start + 0.3));
          if (k <= 0) return null;
          return (
            <div key={text} style={{ opacity: Math.min(1, k * 1.5), transform: `translateX(${(1 - k) * 40}px)`, display: "flex", alignItems: "center", gap: 12, background: c.ink, border: `2px solid ${ok ? c.blue : c.line}`, borderRadius: 14, padding: ok ? "14px 24px" : "10px 20px", boxShadow: "0 12px 40px rgba(0,0,0,.6)" }}>
              {ok ? <Check color={c.blue} size={32} /> : <Cross color={c.faint} size={26} />}
              <div style={{ fontFamily: f.sans, fontWeight: ok ? 700 : 500, fontSize: ok ? 34 : 26, color: ok ? c.text : c.dim, textDecoration: ok ? "none" : "line-through" }}>{text}</div>
            </div>
          );
        })}
      </div>

      {/* Fix: one automatic, one that waits */}
      <Shot t={t} src="shop-failing.jpg" url="lumencoffee.shop/checkout" opacity={fade(t, S.approve.start + 0.2, waitsAt + 0.1)} keys={[{ at: 0, rect: { x: 0, y: 0, w: 1250 } }, { at: S.approve.start, rect: { x: 0, y: 0, w: 1050 }, dur: 3 }]}>
        {(s) => <Ring t={t} at={cue("waits") + 0.5} box={[0, 2, 1600, 40]} color={c.blue} s={s} pad={0} />}
      </Shot>
      <Tag t={t} at={cue("waits") + 0.8} until={waitsAt} x={330} y={300} text="Auto" sub="A warning for shoppers. Safe, so it just ran." color={c.blue} />

      <Shot t={t} src="approve.jpg" opacity={fade(t, waitsAt, CLICK + 0.25, 0.3)} keys={[{ at: 0, rect: { x: 180, y: 180, w: 1240 } }, { at: cue("click") - 0.9, rect: { x: 200, y: 290, w: 820 }, dur: 2.2 }]}>
        {(s) => (
          <>
            <Ring t={t} at={waitsAt + 0.5} until={CLICK + 0.1} box={[224, 317, 1152, 208]} color={c.warn} s={s} />
            <Cursor t={t} from={[820, 640]} to={[300, 486]} start={cue("click") - 0.9} click={CLICK} s={s} />
          </>
        )}
      </Shot>
      <Tag t={t} at={waitsAt + 0.8} until={CLICK} x={1010} y={640} text="Needs approval" sub="It changes the shop, so a person decides" color={c.warn} />
      <Shot t={t} src="approved.jpg" opacity={fade(t, CLICK + 0.1, backAt + 0.15, 0.25)} keys={[{ at: 0, rect: { x: 200, y: 420, w: 820 } }]}>
        {(s) => <Ring t={t} at={CLICK + 0.2} box={[224, 533, 1152, 198]} color={c.alive} s={s} />}
      </Shot>
      <Shot t={t} src="shop-fixed.jpg" url="lumencoffee.shop/checkout" opacity={fade(t, backAt, S.recover.start + 0.5)} keys={[{ at: 0, rect: { x: 300, y: 20, w: 1000 } }, { at: backAt, rect: { x: 300, y: 20, w: 760 }, dur: 4 }]}>
        {(s) => <Ring t={t} at={backAt + 0.4} box={[352, 194, 118, 30]} color={c.alive} s={s} />}
      </Shot>
      <Tag t={t} at={backAt + 0.6} until={S.recover.start + 0.3} x={1130} y={500} text="Back in dollars" sub="Checkout works again" color={c.alive} />

      {/* The flash when the line comes back */}
      {t > REVIVE - 0.05 && t < REVIVE + 0.9 ? <div style={{ position: "absolute", inset: 0, background: `radial-gradient(1200px 500px at 600px 40px, ${c.alive}, transparent 70%)`, opacity: 0.5 * (1 - lin(t, REVIVE, REVIVE + 0.9)) }} /> : null}
      {t > BREAK_DEMO && t < BREAK_DEMO + 0.7 ? <div style={{ position: "absolute", inset: 0, background: c.flat, opacity: 0.22 * (1 - lin(t, BREAK_DEMO, BREAK_DEMO + 0.7)) }} /> : null}
    </>
  );
};
