import React from "react";
import { c, f } from "../theme";
import { Pulse } from "../Pulse";
import { BREAK_OPEN, REWIND, SCENES, cue, cueEnd, lin, mix, pop, ramp, window as win } from "../time";
import { Check, money } from "../ui";

const PERIOD = 0.92;
const FIRST = 0.35 + 0.33 * PERIOD;
const beatsBefore = (t: number) => Math.max(0, Math.floor((Math.min(t, BREAK_OPEN) - FIRST) / PERIOD) + 1);

const DAYS = ["FRIDAY", "SATURDAY", "SUNDAY", "MONDAY"];
/** Minutes since Friday 00:00 → "FRIDAY 18:04". */
const clock = (m: number) => {
  const d = Math.min(3, Math.floor(m / 1440));
  const hh = Math.floor((m % 1440) / 60);
  const mm = Math.floor(m % 60);
  return { day: DAYS[d], time: `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}` };
};
const BROKE = 18 * 60 + 4;
const FOUND = 3 * 1440 + 9 * 60 + 12;

/** The cold open: a shop's revenue as a heartbeat, the Friday it stops, and the Monday someone notices. */
export const Open: React.FC<{ t: number }> = ({ t }) => {
  const end = SCENES.title.start + 2.3;
  if (t > end) return null;
  const lapseA = cue("monday") + 0.2;
  const lapseB = cueEnd("monday") - 0.9;
  const rewind = lin(t, REWIND, REWIND + 1.3);
  const minutes =
    t < BREAK_OPEN ? BROKE - (BREAK_OPEN - t) * 0.5 : t < REWIND ? mix(BROKE, FOUND, Math.pow(lin(t, lapseA, lapseB), 1.6)) : mix(FOUND, BROKE - 6, 1 - Math.pow(1 - rewind, 3));
  const { day, time } = clock(minutes);
  const beats = beatsBefore(t);
  const dead = t >= BREAK_OPEN && t < REWIND;
  const sinceBeat = t < BREAK_OPEN ? (t - FIRST) % PERIOD : 9;
  const oncall = win(t, cue("oncall") - 0.2, REWIND + 0.1, 0.5);
  const dimPulse = 1 - 0.55 * oncall;
  const out = 1 - lin(t, end - 0.9, end);
  const chips = ["API · 200 OK", "CPU · 31%", "UPTIME · 100%", "ALL DASHBOARDS GREEN"];
  return (
    <div style={{ position: "absolute", inset: 0, opacity: out }}>
      <div style={{ position: "absolute", left: 96, top: 84, opacity: ramp(t, 0.3, 1.2) }}>
        <div style={{ fontFamily: f.mono, fontSize: 20, letterSpacing: 3, color: c.faint }}>LUMEN COFFEE CO. · REVENUE</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginTop: 10 }}>
          <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 46, color: dead ? c.flat : c.text, letterSpacing: 2 }}>{time}</div>
          <div style={{ fontFamily: f.mono, fontSize: 26, color: c.dim, letterSpacing: 3 }}>{day}</div>
          {t >= REWIND ? <div style={{ fontFamily: f.mono, fontSize: 20, color: c.blue, letterSpacing: 3, opacity: 1 - lin(t, REWIND + 1.3, REWIND + 1.8) }}>◀◀ REWIND</div> : null}
        </div>
      </div>

      <div style={{ position: "absolute", right: 96, top: 84, textAlign: "right", opacity: ramp(t, 0.6, 1.5) }}>
        <div style={{ fontFamily: f.mono, fontSize: 20, letterSpacing: 3, color: c.faint }}>{dead ? "SALES SINCE 18:04" : "SALES TODAY"}</div>
        <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 84, lineHeight: 1.05, marginTop: 6, color: dead ? c.flat : c.text, fontVariantNumeric: "tabular-nums", transform: `scale(${dead ? 1 + 0.12 * (1 - lin(t, BREAK_OPEN, BREAK_OPEN + 0.5)) : 1})`, transformOrigin: "100% 50%" }}>
          {dead ? "$0" : money(1242 + beats * 18)}
        </div>
      </div>

      <div style={{ position: "absolute", left: 0, top: 330, opacity: ramp(t, 0.2, 1.4) * dimPulse, transform: `translateY(${oncall * 250}px)` }}>
        <Pulse t={t} width={1500} height={360} seconds={6.5} stroke={5} />
        {t < BREAK_OPEN && sinceBeat >= 0 && sinceBeat < 0.8 && beats > 0 ? (
          <div style={{ position: "absolute", left: 1530, top: 120 - sinceBeat * 90, fontFamily: f.mono, fontWeight: 600, fontSize: 40, color: c.alive, opacity: 1 - sinceBeat / 0.8 }}>+$18</div>
        ) : null}
        {dead ? (
          <div style={{ position: "absolute", left: 1530, top: 190, fontFamily: f.mono, fontWeight: 600, fontSize: 26, letterSpacing: 3, color: c.flat, opacity: (0.55 + 0.45 * Math.sin(t * 7)) * ramp(t, BREAK_OPEN + 0.3, BREAK_OPEN + 0.8) }}>NO PAYMENTS</div>
        ) : null}
      </div>

      <div style={{ position: "absolute", left: 96, top: 770, display: "flex", gap: 18, opacity: 1 - oncall }}>
        {chips.map((chip, i) => {
          const k = pop(t, cue("monday") + 0.25 + i * 0.22, 0.45);
          return (
            <div key={chip} style={{ opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 16}px)`, display: "flex", alignItems: "center", gap: 10, fontFamily: f.mono, fontSize: 24, color: c.dim, border: `1.5px solid ${c.line}`, background: c.panel, borderRadius: 12, padding: "12px 20px" }}>
              <Check size={24} />
              {chip}
            </div>
          );
        })}
      </div>

      {oncall > 0 ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 250, textAlign: "center", opacity: oncall }}>
          <div style={{ fontFamily: f.sans, fontWeight: 600, fontSize: 70, color: c.dim, letterSpacing: -1.5, transform: `translateY(${(1 - ramp(t, cue("oncall"), cue("oncall") + 0.7)) * 24}px)` }}>We put people on call for servers.</div>
          <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 124, color: c.text, marginTop: 14, letterSpacing: -1, opacity: ramp(t, cue("oncall") + 2.3, cue("oncall") + 2.9), transform: `translateY(${(1 - ramp(t, cue("oncall") + 2.3, cue("oncall") + 3.1)) * 30}px)` }}>
            Nobody is on call for the <span style={{ color: c.flat }}>money.</span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
