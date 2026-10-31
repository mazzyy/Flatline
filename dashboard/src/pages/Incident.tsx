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

  if (!row) return <p className="muted">{err || "Loading…"}</p>;
  const pendingCount = (row.proposals || []).filter((p) => p.status === "pending").length;
  return (
    <div>
      <a className="back" href="#/overview">← Back to overview</a>
      <h1>{row.title || row.playbook}</h1>
      <p className="proposal-head">
        <span className={`badge ${row.status}`}>{row.status.replace(/_/g, " ")}</span>
        <span className="mono muted">{row.playbook}</span>
        {pendingCount > 0 && <span className="badge approval">{pendingCount} awaiting your approval</span>}
      </p>
      <div className="card">
        <h3>Root cause</h3>
        <p style={{ marginTop: 0 }}>{row.root_cause || "Still diagnosing…"}</p>
        {(row.evidence?.claims || []).map((c) => (
          <div key={c.ref} className="evidence">
            {c.claim} <span className="badge info">{c.source}:{c.ref}</span>
          </div>
        ))}
        {row.notes && <pre>{row.notes}</pre>}
      </div>
      <h2>Proposals</h2>
      {!(row.proposals || []).length && <p className="muted">No proposals yet. The agents are still working.</p>}
      {(row.proposals || []).map((p) => (
        <div className="card" key={p.id} style={{ marginBottom: "0.7rem" }}>
          <div className="proposal-head">
            <code>{p.action}</code>
            <span className={`badge ${p.tier}`}>{p.tier}</span>
            <span className={`badge ${p.status}`}>{p.status}</span>
          </div>
          <p style={{ color: "var(--pp-ink-2)" }}>{p.rationale}</p>
          {p.status === "pending" && (
            <div className="proposal-actions">
              <button onClick={() => void decide(p.id, "approve")}>Approve</button>
              <button className="danger" onClick={() => void decide(p.id, "reject")}>Reject</button>
            </div>
          )}
          {(p.executions || []).map((e) => (
            <details key={e.id}>
              <summary>
                Execution <span className={`badge ${e.success ? "executed" : "failed"}`}>{e.success ? "success" : "failed"}</span>
                {e.error && <span className="muted"> · {e.error}</span>}
              </summary>
              <pre>{JSON.stringify(e.response, null, 2)}</pre>
            </details>
          ))}
        </div>
      ))}
      <h2>Agent timeline</h2>
      <p className="muted" style={{ marginTop: 0 }}>Every node call with its input, output and tool calls, exactly as persisted.</p>
      {(row.steps || []).map((s) => (
        <details key={s.id}>
          <summary>
            <strong>{s.node}</strong> <span className="muted">· {s.model} · {s.latency_ms}ms</span>
          </summary>
          <pre>{JSON.stringify({ input: s.input, output: s.output, tool_calls: s.tool_calls }, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
