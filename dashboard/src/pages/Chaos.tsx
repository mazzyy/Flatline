import { useState } from "react";
import { authHeaders, post } from "../api";

const ACTIONS: { label: string; body: Record<string, unknown> }[] = [
  {
    label: "Inject checkout failures (declines)",
    body: { chaos: { mock_response: "INSTRUMENT_DECLINED" }, note: "declines" },
  },
  {
    label: "Inject checkout failures (server errors)",
    body: { chaos: { mock_response: "INTERNAL_SERVER_ERROR" }, note: "server errors" },
  },
  {
    label: "Ship bad currency config",
    body: { chaos: { bad_currency: true }, note: "bad currency" },
  },
  {
    label: "Inject refund wave",
    body: { chaos: { inject: "refund_wave" }, note: "refund wave" },
  },
  {
    label: "Inject subscription renewal failures",
    body: { chaos: { inject: "renewal_failures" }, note: "renewals" },
  },
  {
    label: "Break webhook endpoint (stretch)",
    body: { chaos: { webhook_broken: true }, note: "webhook gap" },
  },
  { label: "Reset all chaos", body: { reset: true } },
];

type ChaosResult = {
  injected?: string[];
  incidents?: string[];
};

export default function ChaosPage() {
  const [msg, setMsg] = useState("");

  async function run(body: Record<string, unknown>, label: string) {
    setMsg("working…");
    try {
      const result = await post<ChaosResult>("/api/chaos", body, authHeaders());
      const injected = result.injected?.length || 0;
      const incidents = result.incidents?.length || 0;
      setMsg(`${label}: done · ${injected} events · ${incidents} incidents`);
    } catch (e) {
      setMsg(String(e));
    }
  }

  return (
    <div>
      <h1>Chaos panel</h1>
      <p className="muted">Judge controls. Synthetic events are stored with a simulated badge.</p>
      {ACTIONS.map((a) => (
        <p key={a.label}>
          <button className={a.body.reset ? "secondary" : undefined} onClick={() => void run(a.body, a.label)}>
            {a.label}
          </button>
        </p>
      ))}
      <p>{msg}</p>
    </div>
  );
}
