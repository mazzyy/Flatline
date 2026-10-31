import { useCallback, useEffect, useState } from "react";
import { get, post } from "../api";

type Evidence = { claim: string; source: string; ref: string };
type Step = { id: string; node: string; model: string; latency_ms: number; input: unknown; output: unknown; tool_calls: unknown };
type Execution = { id: string; success: boolean; error?: string; response: unknown };
type Proposal = {
  id: string;
  action: string;
  tier: string;
  status: string;
  rationale: string;
  params: unknown;
  executions?: Execution[];
};
type Detail = {
  id: string;
  title: string;
  playbook: string;
  status: string;
  root_cause?: string;
  evidence?: { claims?: Evidence[] };
  notes?: string;
  steps?: Step[];
  proposals?: Proposal[];
};

export default function IncidentPage({ id }: { id: string }) {
  const [row, setRow] = useState<Detail | null>(null);
  const [err, setErr] = useState("");

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      setRow(await get<Detail>(`/api/incidents/${id}`));
    } catch (e) {
      setErr(String(e));
    }
  }, [id]);

  useEffect(() => {
    void refresh();
    const on = () => void refresh();
    window.addEventListener("warden-sse", on);
    return () => window.removeEventListener("warden-sse", on);
  }, [refresh]);

  async function decide(proposalId: string, kind: "approve" | "reject") {
    await post(`/api/proposals/${proposalId}/${kind}`, {});
    await refresh();
  }

  if (!row) return <p>{err || "Loading…"}</p>;
  return (
    <div>
      <p><a href="#/overview">← Overview</a></p>
      <h1>{row.title || row.playbook}</h1>
      <p>
        <span className="badge">{row.status}</span> <span className="mono">{row.playbook}</span>
      </p>
      <div className="card">
        <h2>Root cause</h2>
        <p>{row.root_cause || "Still diagnosing."}</p>
        {(row.evidence?.claims || []).map((c) => (
          <p key={c.ref} className="muted">
            {c.claim} <span className="badge">{c.source}:{c.ref}</span>
          </p>
        ))}
        {row.notes && <pre>{row.notes}</pre>}
      </div>
      <h2>Agent timeline</h2>
      {(row.steps || []).map((s) => (
        <details key={s.id}>
          <summary>
            <strong>{s.node}</strong> · {s.model} · {s.latency_ms}ms
          </summary>
          <pre>{JSON.stringify({ input: s.input, output: s.output, tool_calls: s.tool_calls }, null, 2)}</pre>
        </details>
      ))}
      <h2>Proposals</h2>
      {(row.proposals || []).map((p) => (
        <div className="card" key={p.id} style={{ marginBottom: "0.7rem" }}>
          <div>
            <code>{p.action}</code> <span className={`badge ${p.tier}`}>{p.tier}</span>{" "}
            <span className={`badge ${p.status}`}>{p.status}</span>
          </div>
          <p>{p.rationale}</p>
          {p.status === "pending" && (
            <p>
              <button onClick={() => void decide(p.id, "approve")}>Approve</button>{" "}
              <button className="danger" onClick={() => void decide(p.id, "reject")}>Reject</button>
            </p>
          )}
          {(p.executions || []).map((e) => (
            <pre key={e.id}>{JSON.stringify(e, null, 2)}</pre>
          ))}
        </div>
      ))}
    </div>
  );
}
