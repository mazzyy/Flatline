import React from "react";
import { Img, staticFile } from "remotion";
import { c, f } from "../theme";
import { Pulse } from "../Pulse";
import { SCENES, TOTAL, cue, lin, pop, ramp, window as win } from "../time";

const STACK = ["PayPal Sandbox REST", "PayPal MCP server", "Webhooks", "Invoicing", "JS SDK v6", "Gemini · or a local Qwen", "Python · FastAPI", "React · AG Grid"];

export const Close: React.FC<{ t: number }> = ({ t }) => {
  const S = SCENES.close;
  if (t < S.start) return null;
  const lineAt = cue("oneline") - 0.3;
  const tagAt = cue("tag") - 0.5;
  const WORDS: [string, number, string][] = [
    ["Notices.", 0.25, c.text],
    ["Fixes.", 2.45, c.text],
    ["Gets the lost sales back.", 3.25, c.alive],
  ];
  return (
    <>
      {t < lineAt + 0.4 ? (
        <div style={{ position: "absolute", inset: 0, opacity: win(t, S.start + 0.4, lineAt + 0.3, 0.4) }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 300, textAlign: "center", fontFamily: f.mono, fontSize: 24, letterSpacing: 6, color: c.faint }}>BUILT ON</div>
          <div style={{ position: "absolute", left: 230, right: 230, top: 380, display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 20 }}>
            {STACK.map((s, i) => {
              const k = pop(t, cue("stack") + 0.15 + i * 0.22, 0.45);
              const paypal = i < 5;
              return (
                <div key={s} style={{ opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 20}px)`, fontFamily: f.sans, fontWeight: 600, fontSize: 40, color: paypal ? c.text : c.dim, border: `2px solid ${paypal ? c.blue + "99" : c.line}`, background: c.panel, borderRadius: 999, padding: "16px 34px" }}>
                  {s}
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {t >= lineAt && t < tagAt + 0.4 ? (
        <div style={{ position: "absolute", left: 200, top: 300, opacity: win(t, lineAt, tagAt + 0.3, 0.35) }}>
          {WORDS.map(([w, dt, col]) => {
            const k = ramp(t, cue("oneline") + dt, cue("oneline") + dt + 0.6);
            return (
              <div key={w} style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 138, letterSpacing: -5, lineHeight: 1.12, color: col, opacity: k, transform: `translateX(${(1 - k) * -40}px)` }}>
                {w}
              </div>
            );
          })}
        </div>
      ) : null}

      {t >= tagAt ? (
        <div style={{ position: "absolute", inset: 0, opacity: ramp(t, tagAt, tagAt + 0.6) * (1 - lin(t, TOTAL - 0.7, TOTAL - 0.05)) }}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 210, textAlign: "center", fontFamily: f.sans, fontWeight: 800, fontSize: 230, letterSpacing: -9, color: c.text, lineHeight: 1 }}>Flatline</div>
          <div style={{ position: "absolute", left: 0, top: 470 }}>
            <Pulse t={t} width={1920} height={150} seconds={7} stroke={4} head={false} />
          </div>
          <div style={{ position: "absolute", left: 0, right: 0, top: 626, textAlign: "center", fontFamily: f.serif, fontStyle: "italic", fontSize: 76, color: c.text, opacity: ramp(t, cue("tag") + 0.8, cue("tag") + 1.4) }}>On call for your revenue.</div>
          <div style={{ position: "absolute", left: 0, right: 0, top: 752, display: "flex", justifyContent: "center", opacity: ramp(t, cue("tag") + 1.2, cue("tag") + 1.8) }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18, border: `2px solid ${c.alive}88`, background: c.panel, borderRadius: 999, padding: "14px 34px" }}>
              <div style={{ width: 14, height: 14, borderRadius: 7, background: c.alive, boxShadow: `0 0 18px ${c.alive}` }} />
              <div style={{ fontFamily: f.mono, fontSize: 22, letterSpacing: 4, color: c.alive }}>TRY IT LIVE</div>
              <div style={{ fontFamily: f.mono, fontSize: 30, color: c.text }}>flatline-demo-27612c3a852c.herokuapp.com</div>
            </div>
          </div>
          <div style={{ position: "absolute", left: 0, right: 0, top: 862, display: "flex", justifyContent: "center", alignItems: "center", gap: 22, opacity: ramp(t, cue("tag") + 1.6, cue("tag") + 2.2) }}>
            <Img src={staticFile("brand/builder.jpg")} style={{ width: 84, height: 84, borderRadius: 42, objectFit: "cover", border: `2px solid ${c.line}` }} />
            <div>
              <div style={{ fontFamily: f.sans, fontWeight: 600, fontSize: 32, color: c.text }}>Built by Abdul Musawar Soomro</div>
              <div style={{ fontFamily: f.mono, fontSize: 24, color: c.dim, marginTop: 4 }}>github.com/mazzyy/Flatline · PayPal AI Hackathon 2026</div>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};
