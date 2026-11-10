import { useState } from "react";
import { authHeaders, post } from "../api";

type Action = { label: string; blurb: string; body: Record<string, unknown>; secondary?: boolean; path?: string };

const ACTIONS: Action[] = [
  {
    label: "Inject checkout failures (declines)",
    blurb: "Six buyers hit INSTRUMENT_DECLINED. Expect: alert + banner, no rollback of a healthy config.",
    body: { chaos: { mock_response: "INSTRUMENT_DECLINED" }, note: "declines" },
  },
  {
    label: "Inject checkout failures (server errors)",
    blurb: "PayPal returns INTERNAL_SERVER_ERROR on capture. Expect: alert + banner.",
    body: { chaos: { mock_response: "INTERNAL_SERVER_ERROR" }, note: "server errors" },
  },
  {
    label: "Ship bad currency config",
    blurb: "A new config version sets EUR on a USD shop. Expect: banner (auto) + config rollback (approval).",
    body: { chaos: { bad_currency: true }, note: "bad currency" },
  },
  {
    label: "Inject refund wave",
    blurb: "Five refunds on one product. Expect: pause sales (approval); bulk refund refused and escalated.",
    body: { chaos: { inject: "refund_wave" }, note: "refund wave" },
  },
  {
    label: "Inject subscription renewal failures",
    blurb: "Four failed renewals on Coffee Club. Expect: reminder (auto); capturing a balance needs approval.",
    body: { chaos: { inject: "renewal_failures" }, note: "renewals" },
  },
  {
    label: "Customers pay their recovery requests",
    blurb: "Plays the customers after you approved a recovery: about two thirds pay. Expect: Recovered goes up, marked simulated.",
    body: {},
    path: "/api/synthetic/recovery-payments",
  },
  {
    label: "Break webhook endpoint (stretch)",
    blurb: "The webhook route returns 500. The webhook_gap playbook is disabled by default; this only flips the flag.",
    body: { chaos: { webhook_broken: true }, note: "webhook gap" },
  },
  {
    label: "Reset all chaos",
    blurb: "Clear every flag, banner and pause. Currency back to USD.",
    body: { reset: true },
    secondary: true,
  },
];

type ChaosResult = { injected?: string[]; incidents?: string[] };

export default function ChaosPage() {
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState("");

  async function run(a: Action) {
    setBusy(a.label);
    setErr(false);
    setMsg("Working…");
    try {
      const result = await post<ChaosResult>(a.path || "/api/chaos", a.body, authHeaders());
      const injected = result.injected?.length || 0;
      const incidents = result.incidents?.length || 0;
      setMsg(
        a.path
          ? `${a.label}: ${injected} simulated payment${injected === 1 ? "" : "s"}` + (injected ? "" : " (approve a recovery proposal first)")
          : `${a.label}: done · ${injected} synthetic events · ${incidents} incident${incidents === 1 ? "" : "s"} touched`,
      );
    } catch (e) {
      setErr(true);
      setMsg(String(e));
    } finally {
      setBusy("");
    }
  }

  return (
    <div>
      <h1>Chaos panel</h1>
      <p className="lede">
        Judge controls. Each button writes labeled synthetic events, updates the shop config, and runs the
        detector immediately. Then watch the <a href="#/overview">Overview</a>.
      </p>
      <div className="chaos-grid">
        {ACTIONS.map((a) => (
          <div className="card" key={a.label}>
            <h3>{a.label}</h3>
            <p>{a.blurb}</p>
            <button className={a.secondary ? "secondary" : undefined} disabled={Boolean(busy)} onClick={() => void run(a)}>
              {busy === a.label ? "Working…" : a.secondary ? "Reset" : "Inject"}
            </button>
          </div>
        ))}
      </div>
      {msg && <div className={`result-bar ${err ? "err" : ""}`}>{msg}</div>}
    </div>
  );
}
