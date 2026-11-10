import { useEffect, useState } from "react";
import { get } from "../api";

type Item = { key: string; tier: string; description: string; notes?: string; planner_only?: boolean };
type Limit = { key: string; value: number; meaning: string };

const TIERS: { tier: string; title: string; blurb: string }[] = [
  { tier: "auto", title: "Auto", blurb: "Runs immediately. Low risk, reversible." },
  { tier: "approval", title: "Approval", blurb: "Waits for a human on the incident page." },
  { tier: "forbidden", title: "Forbidden", blurb: "Refused and escalated. Never agent-initiated." },
];

export default function PolicyPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [limits, setLimits] = useState<Limit[]>([]);
  useEffect(() => {
    void get<{ items: Item[]; limits?: Limit[] }>("/api/policy/catalog").then((b) => {
      setItems(b.items);
      setLimits(b.limits || []);
    });
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
                    {i.planner_only && <span className="badge info" style={{ marginLeft: "0.4rem" }}>code only</span>}
                    <div className="desc">{i.description}</div>
                    {i.notes && <div className="desc">{i.notes}</div>}
                  </li>
                ))}
                {!rows.length && <li className="muted">Loading…</li>}
              </ul>
            </div>
          );
        })}
      </div>

      <h2>Money limits</h2>
      <p className="lede">
        The tier is not the whole answer when money is involved. These limits are checked in code on every
        proposal, and no agent can change them.
      </p>
      <div className="card">
        <ul className="tier-list">
          {limits.map((l) => (
            <li key={l.key}>
              <code>{l.key}</code> <strong style={{ marginLeft: "0.4rem" }}>{l.value}</strong>
              <div className="desc">{l.meaning}</div>
            </li>
          ))}
          {!limits.length && <li className="muted">Loading…</li>}
        </ul>
      </div>
    </div>
  );
}
