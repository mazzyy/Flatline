import { useEffect, useState } from "react";
import { get } from "../api";

type Item = { key: string; tier: string; description: string };

const TIERS: { tier: string; title: string; blurb: string }[] = [
  { tier: "auto", title: "Auto", blurb: "Runs immediately. Low risk, reversible." },
  { tier: "approval", title: "Approval", blurb: "Waits for a human on the incident page." },
  { tier: "forbidden", title: "Forbidden", blurb: "Refused and escalated. Never agent-initiated." },
];

export default function PolicyPage() {
  const [items, setItems] = useState<Item[]>([]);
  useEffect(() => {
    void get<{ items: Item[] }>("/api/policy/catalog").then((b) => setItems(b.items));
  }, []);
  return (
    <div>
      <h1>Action catalog</h1>
      <p className="lede">
        The allowlist the policy proxy enforces. Anything not listed is forbidden. The proxy is plain code,
        not a prompt, so an agent cannot talk its way past it.
      </p>
      <div className="tiers">
        {TIERS.map((t) => {
          const rows = items.filter((i) => i.tier === t.tier);
          return (
            <div className="card" key={t.tier}>
              <div className="tier-head">
                <h3>{t.title}</h3>
                <span className={`badge ${t.tier}`}>{rows.length} actions</span>
              </div>
              <p className="muted" style={{ marginTop: 0 }}>{t.blurb}</p>
              <ul className="tier-list">
                {rows.map((i) => (
                  <li key={i.key}>
                    <code>{i.key}</code>
                    <div className="desc">{i.description}</div>
                  </li>
                ))}
                {!rows.length && <li className="muted">Loading…</li>}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}
