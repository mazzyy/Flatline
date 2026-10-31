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
  revenue_at_risk_per_hour: number;
};

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
    window.addEventListener("warden-sse", on);
    const t = setInterval(() => void refresh(), 5000);
    return () => {
      window.removeEventListener("warden-sse", on);
      clearInterval(t);
    };
  }, [refresh]);

  return (
    <div>
      <h1>Revenue health</h1>
      <div className="row">
        <div className="card tile">
          <div className="muted">Score</div>
          <div className="score">{health?.score ?? "—"}</div>
        </div>
        <div className="card tile">
          <div className="muted">Open incidents</div>
          <div className="score">{health?.open_incidents ?? "—"}</div>
        </div>
        <div className="card tile">
          <div className="muted">Captures / failures</div>
          <div className="score">
            {health?.captures ?? 0}/{health?.failures ?? 0}
          </div>
        </div>
      </div>
      <h2>Playbook tiles</h2>
      <div className="row">
        {Object.entries(health?.metrics || {}).map(([name, m]) => (
          <div className="card tile" key={name}>
            <div className="muted">{name}</div>
            <div>
              <strong>{m.current}</strong> vs baseline {m.baseline.toFixed(1)}
            </div>
            {m.breached ? <span className="badge forbidden">breach</span> : <span className="badge auto">quiet</span>}
          </div>
        ))}
      </div>
      <h2>Incidents</h2>
      <ul className="feed">
        {incidents.map((i) => (
          <li key={i.id}>
            <a href={`#/incident/${i.id}`}>{i.title || i.playbook}</a>{" "}
            <span className="badge">{i.status}</span>{" "}
            <span className="muted">${i.revenue_at_risk_per_hour.toFixed(0)}/h at risk</span>
          </li>
        ))}
        {!incidents.length && <li className="muted">No incidents yet. Use the chaos panel.</li>}
      </ul>
    </div>
  );
}
