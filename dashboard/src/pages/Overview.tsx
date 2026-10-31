import { useCallback, useEffect, useState } from "react";
import { get } from "../api";

type Health = {
  score: number;
  captures: number;
  failures: number;
  open_incidents: number;
  metrics: Record<string, { metric: string; current: number; baseline: number; breached: boolean }>;
};

type Incident = {
  id: string;
  title: string;
  playbook: string;
  status: string;
  severity: string;
  created_at: string;
  revenue_at_risk_per_hour: number;
};

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

function pretty(name: string): string {
  return name.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

function when(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Overview() {
  const [health, setHealth] = useState<Health | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const refresh = useCallback(async () => {
    try {
      setHealth(await get<Health>("/api/metrics/health"));
      const body = await get<{ items: Incident[] }>("/api/incidents");
      setIncidents(body.items);
    } catch {
      /* keep last */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const on = () => void refresh();
    window.addEventListener("flatline-sse", on);
    const t = setInterval(() => void refresh(), 5000);
    return () => {
      window.removeEventListener("flatline-sse", on);
      clearInterval(t);
    };
  }, [refresh]);

  const score = health?.score ?? null;
  const scoreClass = score === null ? "" : score >= 80 ? "good" : score < 50 ? "bad" : "";
  const failRate = health && health.captures ? Math.round((health.failures / health.captures) * 100) : 0;
  const openIncidents = incidents.filter((i) => i.status !== "resolved");
  const atRisk = openIncidents.reduce((sum, i) => sum + (i.revenue_at_risk_per_hour || 0), 0);

  return (
    <div>
      <h1>Revenue health</h1>
      <p className="lede">
        Live view of the merchant&apos;s PayPal integration. New here? Read{" "}
        <a href="#/how">how it works</a> or open the <a href="#/chaos">Chaos</a> panel to trigger an incident.
      </p>

      <div className="row">
        <div className="card tile">
          <div className="label">Health score</div>
          <div className={`score ${scoreClass}`}>{score ?? "—"}</div>
          <div className="sub">100 is quiet; incidents and failures lower it</div>
        </div>
        <div className="card tile">
          <div className="label">Open incidents</div>
          <div className={`score ${openIncidents.length ? "bad" : "good"}`}>{health?.open_incidents ?? "—"}</div>
          <div className="sub">{atRisk ? `${usd.format(atRisk)}/h at risk` : "nothing at risk"}</div>
        </div>
        <div className="card tile">
          <div className="label">Captures</div>
          <div className="score">{health?.captures ?? 0}</div>
          <div className="sub">{health?.failures ?? 0} failed · {failRate}% failure rate</div>
        </div>
      </div>

      <h2>Playbooks</h2>
      <div className="row">
        {Object.entries(health?.metrics || {}).map(([name, m]) => (
          <div className="card tile playbook" key={name}>
            <div className="label">{pretty(name)}</div>
            <div className="nums">
              {m.current} <span>now · baseline {m.baseline.toFixed(1)}</span>
            </div>
            {m.breached ? <span className="badge forbidden">Breach</span> : <span className="badge auto">Quiet</span>}
          </div>
        ))}
      </div>

      <h2>Incidents</h2>
      <div className="card">
        <ul className="feed">
          {incidents.map((i) => (
            <li key={i.id}>
              <div className="grow">
                <a href={`#/incident/${i.id}`}>{i.title || pretty(i.playbook)}</a>
                <div className="muted" style={{ fontSize: "0.85rem" }}>
                  {pretty(i.playbook)} · {when(i.created_at)}
                </div>
              </div>
              <span className={`badge ${i.status}`}>{i.status.replace(/_/g, " ")}</span>
              <span className="amount">{usd.format(i.revenue_at_risk_per_hour || 0)}/h</span>
            </li>
          ))}
          {!incidents.length && <li className="empty">No incidents yet. Use the Chaos panel to create one.</li>}
        </ul>
      </div>
    </div>
  );
}
