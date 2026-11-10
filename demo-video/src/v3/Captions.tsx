import React from "react";
import { c, f } from "./theme";
import { LINES, lin, ramp } from "./time";

/** Split a line into caption cards of at most ~62 characters, timed by their share of the words. */
const cards = LINES.flatMap((l) => {
  // Sentences first, then clauses, so a card never ends in the middle of a thought.
  const parts: string[] = [];
  for (const sentence of l.text.match(/[^.!?]+[.!?]+["”]?|[^.!?]+$/g) ?? [l.text]) {
    const s = sentence.trim();
    if (!s) continue;
    const last = parts[parts.length - 1];
    if (last && (last + " " + s).length <= 64) parts[parts.length - 1] = last + " " + s;
    else if (s.length <= 64) parts.push(s);
    else {
      let cur = "";
      for (const clause of s.split(/(?<=[,:])\s+/)) {
        if (cur && (cur + " " + clause).length > 64) {
          parts.push(cur);
          cur = clause;
        } else cur = cur ? cur + " " + clause : clause;
      }
      if (cur) parts.push(cur);
    }
  }
  const total = parts.reduce((a, p) => a + p.length, 0);
  let at = l.start;
  return parts.map((p, i) => {
    const dur = ((l.end - l.start) * p.length) / total;
    const card = { text: p, start: at, end: i === parts.length - 1 ? l.end + 0.35 : at + dur };
    at += dur;
    return card;
  });
});

export const Captions: React.FC<{ t: number }> = ({ t }) => {
  const card = cards.find((k) => t >= k.start - 0.05 && t < k.end);
  if (!card) return null;
  const k = Math.min(ramp(t, card.start - 0.05, card.start + 0.18), 1 - lin(t, card.end - 0.15, card.end));
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, display: "flex", justifyContent: "center", opacity: k }}>
      <div style={{ fontFamily: f.sans, fontWeight: 500, fontSize: 31, color: c.text, background: "rgba(7,9,12,.78)", padding: "9px 22px", borderRadius: 12, letterSpacing: 0.1 }}>{card.text}</div>
    </div>
  );
};
