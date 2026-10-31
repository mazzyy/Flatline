import { useEffect, useState } from "react";
import { get } from "../api";

type Item = { key: string; tier: string; description: string };

export default function PolicyPage() {
  const [items, setItems] = useState<Item[]>([]);
  useEffect(() => {
    void get<{ items: Item[] }>("/api/policy/catalog").then((b) => setItems(b.items));
  }, []);
  return (
    <div>
      <h1>Action catalog</h1>
      <p className="muted">Allowlist. Anything else is forbidden. The proxy is plain code, not a prompt.</p>
      {items.map((i) => (
        <div className="card" key={i.key} style={{ marginBottom: "0.5rem" }}>
          <code>{i.key}</code> <span className={`badge ${i.tier}`}>{i.tier}</span>
          <div className="muted">{i.description}</div>
        </div>
      ))}
    </div>
  );
}
