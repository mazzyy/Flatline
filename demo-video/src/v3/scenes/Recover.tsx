import React from "react";
import { c, f } from "../theme";
import { PAYMENTS, RECOVERY_CLICK, SCENES, cue, lin, mix, pop, ramp, window as win } from "../time";
import { Check, Cross, Cursor, Ring, Shot, Tag } from "../ui";

const GX = 130;
const GY = 300;
const CW = 318;
const CH = 196;
const GAP = 24;
const cell = (i: number) => ({ x: GX + (i % 3) * (CW + GAP), y: GY + Math.floor(i / 3) * (CH + GAP) });
const ORDERS = ["DFD47F8E", "0F32E169", "73CA7F58", "70ACE640", "D31B820D", "922E0F98"];

/** The part most tools do not have: after the fix, go and get the lost sales back. */
export const Recover: React.FC<{ t: number }> = ({ t }) => {
  const S = SCENES.recover;
  if (t < S.start || t > SCENES.trust.start + 0.5) return null;
  const sixAt = cue("six");
  const shotA = cue("after") + 2.4;
  const shotB = RECOVERY_CLICK + 0.45;
  const realOut = cue("play") - 0.75; // the real sandbox invoice, then the six cards
  const sentAt = realOut - 0.3;
  const paidAt = shotB + (realOut - shotB) * 0.56;
  const codeAt = cue("code") - 0.4;
  const paid = PAYMENTS.filter((p) => t >= p).length;
  const gridOut = sixAt + 3.45; // the AG Grid view of the six failed payments, then the cards
  const cardsAt = gridOut - 0.25;
  const lostCards = win(t, cardsAt, shotA + 0.1, 0.35);
  const invoices = win(t, sentAt, codeAt + 0.2, 0.4);
  const seventy = ramp(t, cue("seventy") - 0.1, cue("seventy") + 0.5);
  const lastPay = PAYMENTS.filter((p) => t >= p).pop() ?? -9;
  const bump = 1 + 0.16 * Math.max(0, 1 - (t - lastPay) / 0.35);
  return (
    <>
      {/* "Most tools stop here." */}
      {t < sixAt ? (
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", opacity: win(t, S.start + 0.5, sixAt - 0.2, 0.4) * mix(1, 0.28, lin(t, cue("stop") + 2.4, cue("stop") + 4)) }}>
          <div style={{ display: "flex", alignItems: "center", gap: 22, border: `3px solid ${c.alive}`, borderRadius: 22, padding: "22px 44px", transform: `scale(${0.9 + 0.1 * pop(t, S.start + 0.6, 0.5)}) rotate(-3deg)` }}>
            <Check size={64} />
            <div style={{ fontFamily: f.mono, fontWeight: 600, fontSize: 76, letterSpacing: 8, color: c.alive }}>RESOLVED</div>
          </div>
          <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 66, color: c.dim, marginTop: 44, opacity: ramp(t, cue("stop") + 0.2, cue("stop") + 0.9) }}>Most tools stop here.</div>
        </div>
      ) : null}

      {/* Six people who tried to pay */}
      {lostCards > 0
        ? ORDERS.map((id, i) => {
            const k = pop(t, cardsAt + 0.15 + i * 0.13, 0.45);
            const { x, y } = cell(i);
            return (
              <div key={id} style={{ position: "absolute", left: x, top: y, width: CW, height: CH, boxSizing: "border-box", opacity: Math.min(1, k * 1.5) * lostCards, transform: `translateY(${(1 - k) * 26}px)`, background: c.panel, border: `2px solid ${c.flat}66`, borderRadius: 18, padding: "20px 22px" }}>
                <div style={{ fontFamily: f.mono, fontSize: 17, color: c.faint, letterSpacing: 1.5 }}>ORDER {id}</div>
                <div style={{ fontFamily: f.sans, fontWeight: 600, fontSize: 28, color: c.text, marginTop: 8 }}>House Blend</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 26 }}>
                  <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 46, color: c.text }}>$18</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: f.mono, fontWeight: 600, fontSize: 17, color: c.flat, letterSpacing: 1 }}>
                    <Cross size={20} /> PAYMENT FAILED
                  </div>
                </div>
              </div>
            );
          })
        : null}
      {lostCards > 0 ? (
        <div style={{ position: "absolute", left: 1230, top: 330, opacity: lostCards }}>
          <div style={{ fontFamily: f.mono, fontSize: 22, letterSpacing: 4, color: c.faint }}>LOST WHILE WE WERE DOWN</div>
          <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 190, color: c.flat, letterSpacing: -6, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>${18 * Math.min(6, Math.max(0, Math.floor((t - cardsAt - 0.15) / 0.13) + 1))}</div>
          <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 44, color: c.dim }}>six people who wanted coffee</div>
        </div>
      ) : null}

      {/* The same six, in the transactions grid (AG Grid, server-side rows) */}
      <Shot t={t} src="aggrid.jpg" url="flatline · transactions (AG Grid)" opacity={win(t, sixAt - 0.35, gridOut, 0.3)} keys={[{ at: 0, rect: { x: 190, y: 130, w: 1220 } }, { at: sixAt - 0.2, rect: { x: 205, y: 215, w: 1010 }, dur: 3.2 }]}>
        {(s) => <Ring t={t} at={sixAt + 0.5} box={[224, 334, 1152, 150]} color={c.flat} s={s} pad={4} />}
      </Shot>
      <Tag t={t} at={sixAt + 0.9} until={gridOut} x={1090} y={690} text="Six failed payments" sub="Filtered in the transactions grid (AG Grid)" color={c.flat} />

      {/* The recovery proposal, on the real dashboard */}
      <Shot t={t} src="recovery-pending.jpg" opacity={win(t, shotA, shotB, 0.35)} keys={[{ at: 0, rect: { x: 170, y: 150, w: 1100 } }, { at: shotA + 0.3, rect: { x: 200, y: 290, w: 860 }, dur: 3 }]}>
        {(s) => (
          <>
            <Ring t={t} at={shotA + 0.9} until={RECOVERY_CLICK - 1.3} box={[240, 366, 335, 212]} color={c.blue} s={s} />
            <Ring t={t} at={RECOVERY_CLICK - 1.2} box={[245, 589, 345, 47]} color={c.warn} s={s} />
            <Cursor t={t} from={[900, 700]} to={[420, 613]} start={RECOVERY_CLICK - 1.5} click={RECOVERY_CLICK} s={s} />
          </>
        )}
      </Shot>
      <Tag t={t} at={shotA + 1.2} until={RECOVERY_CLICK - 1.3} x={1090} y={430} text="Six customers, found" sub="From the failed payments themselves" color={c.blue} />
      <Tag t={t} at={RECOVERY_CLICK - 1.1} until={shotB} x={1090} y={760} text="One more approval" sub="Nothing is sent until I say so" color={c.warn} />

      {/* One of them for real: an invoice this code sent in the PayPal sandbox, and a sandbox buyer paying it */}
      <Shot t={t} src="invoice-real.jpg" url="sandbox.paypal.com/invoice" opacity={win(t, shotB - 0.1, paidAt + 0.15, 0.3)} keys={[{ at: 0, rect: { x: 30, y: 40, w: 1500 } }, { at: shotB, rect: { x: 50, y: 150, w: 1120 }, dur: 3 }]}>
        {(s) => <Ring t={t} at={shotB + 0.9} box={[103, 474, 915, 70]} color={c.alive} s={s} />}
      </Shot>
      <Tag t={t} at={shotB + 0.5} until={paidAt} x={1090} y={770} text="A real PayPal invoice" sub="Sent by this code in the PayPal sandbox" color={c.alive} />
      <Shot t={t} src="invoice-paid.jpg" url="sandbox.paypal.com/invoice" opacity={win(t, paidAt, realOut, 0.3)} keys={[{ at: 0, rect: { x: 200, y: 20, w: 1200 } }, { at: paidAt, rect: { x: 280, y: 30, w: 1040 }, dur: 2.2 }]}>
        {(s) => <Ring t={t} at={paidAt + 0.35} box={[590, 118, 400, 180]} color={c.alive} s={s} />}
      </Shot>
      <Tag t={t} at={paidAt + 0.4} until={realOut} x={1090} y={770} text="Paid for real" sub="By a sandbox buyer, in the PayPal sandbox" color={c.alive} />

      {/* Six invoices go out, four come back paid */}
      {invoices > 0
        ? ORDERS.map((id, i) => {
            const at = sentAt + i * 0.09;
            const k = ramp(t, at, at + 0.7);
            const { x, y } = cell(i);
            const isPaid = i < paid;
            const flip = isPaid ? pop(t, PAYMENTS[i], 0.45) : 0;
            const col = isPaid ? c.alive : c.line;
            return (
              <div key={id} style={{ position: "absolute", left: mix(820, x, k), top: mix(520, y, k), width: CW, height: CH, boxSizing: "border-box", opacity: Math.min(1, k * 2) * invoices, transform: `scale(${mix(0.5, 1, k) * (1 + 0.07 * Math.sin(Math.min(1, flip) * Math.PI))})`, background: isPaid ? "#0E1F18" : c.paper, border: `2px solid ${col}`, borderRadius: 18, padding: "18px 22px", boxShadow: isPaid ? `0 0 50px ${c.alive}44` : "0 18px 50px rgba(0,0,0,.5)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontFamily: f.mono, fontSize: 16, letterSpacing: 1.5, color: isPaid ? c.alive : "#5B6470" }}>
                  <span>PAYPAL INVOICE</span>
                  <span>{id}</span>
                </div>
                <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 25, lineHeight: 1.15, color: isPaid ? c.text : c.ink, marginTop: 10 }}>“The failure was on our side. You were not charged.”</div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 12 }}>
                  <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 42, color: isPaid ? c.alive : c.ink }}>$18</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: f.mono, fontWeight: 600, fontSize: 18, letterSpacing: 1.5, color: isPaid ? c.alive : "#5B6470" }}>
                    {isPaid ? <Check size={22} /> : null}
                    {isPaid ? "PAID" : "SENT"}
                  </div>
                </div>
              </div>
            );
          })
        : null}
      {invoices > 0 ? (
        <div style={{ position: "absolute", left: 1230, top: 296, opacity: invoices * ramp(t, sentAt + 0.4, sentAt + 0.9) }}>
          <div style={{ fontFamily: f.mono, fontSize: 22, letterSpacing: 4, color: c.faint }}>RECOVERED</div>
          <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: mix(190, 230, seventy), color: paid ? c.alive : c.faint, letterSpacing: -6, lineHeight: 1.05, fontVariantNumeric: "tabular-nums", transform: `scale(${bump})`, transformOrigin: "0 60%", textShadow: paid ? `0 0 80px ${c.alive}55` : "none" }}>${paid * 18}</div>
          <div style={{ fontFamily: f.serif, fontStyle: "italic", fontSize: 44, color: c.dim }}>of $108 lost</div>
          <div style={{ marginTop: 26, maxWidth: 560, fontFamily: f.mono, fontSize: 21, lineHeight: 1.5, color: c.dim, opacity: ramp(t, cue("play"), cue("play") + 0.5), borderLeft: `3px solid ${c.line}`, paddingLeft: 16 }}>
            DEMO: one invoice was sent and paid for real in the PayPal sandbox (just shown). The four payments counted here are simulated: I play the customers.
          </div>
        </div>
      ) : null}

      {/* No model writes the invoice */}
      {t >= codeAt ? (
        <div style={{ position: "absolute", inset: 0, opacity: win(t, codeAt + 0.2, SCENES.trust.start + 0.4, 0.4) }}>
          <div style={{ position: "absolute", left: 150, top: 205, fontFamily: f.serif, fontStyle: "italic", fontSize: 76, color: c.text }}>
            Who gets an invoice, and for how much, is <span style={{ color: c.blue }}>plain code.</span>
          </div>
          {(
            [
              ["THE FAILED PAYMENT", "$18.00", "what the customer tried to pay", c.text, 0.6],
              ["CODE READS IT AGAIN", "$18.00", "at the moment of sending", c.blue, 1.5],
              ["THE INVOICE", "$18.00", "always the event's amount", c.alive, 2.4],
            ] as [string, string, string, string, number][]
          ).map(([label, amount, sub, col, dt], i) => {
            const k = pop(t, cue("code") + dt, 0.5);
            return (
              <React.Fragment key={label}>
                {i ? <div style={{ position: "absolute", left: 150 + i * 560 - 86, top: 500, width: 60, height: 4, background: c.line, opacity: k }} /> : null}
                <div style={{ position: "absolute", left: 150 + i * 560, top: 380, width: 450, boxSizing: "border-box", opacity: Math.min(1, k * 1.5), transform: `translateY(${(1 - k) * 24}px)`, background: c.panel, border: `2px solid ${col}66`, borderRadius: 20, padding: "26px 30px" }}>
                  <div style={{ fontFamily: f.mono, fontSize: 19, letterSpacing: 2.5, color: c.faint }}>{label}</div>
                  <div style={{ fontFamily: f.sans, fontWeight: 800, fontSize: 92, color: col, letterSpacing: -3 }}>{amount}</div>
                  <div style={{ fontFamily: f.sans, fontSize: 25, color: c.dim }}>{sub}</div>
                </div>
              </React.Fragment>
            );
          })}
          <div style={{ position: "absolute", left: 150, top: 720, display: "flex", alignItems: "center", gap: 20, opacity: ramp(t, cue("code") + 4.6, cue("code") + 5.2), transform: `translateX(${(1 - ramp(t, cue("code") + 4.6, cue("code") + 5.3)) * -30}px)` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, border: `2px solid ${c.flat}88`, borderRadius: 16, padding: "14px 24px", background: c.panel }}>
              <Cross size={34} />
              <div style={{ fontFamily: f.sans, fontWeight: 700, fontSize: 40, color: c.flat, textDecoration: "line-through" }}>$999.00</div>
            </div>
            <div style={{ fontFamily: f.sans, fontSize: 30, color: c.dim, maxWidth: 1100 }}>
              In the tests, a tampered proposal asks for $999. The invoice still says <span style={{ color: c.text, fontWeight: 700 }}>$18.</span>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
};
