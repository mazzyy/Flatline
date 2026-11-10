import { useCallback, useEffect, useState } from "react";
import { get, post } from "../api";

type Evidence = { claim: string; source: string; ref: string };
type ToolCall = { tool: string; via?: string; result?: string; mcp_error?: string };
type Step = { id: string; node: string; model: string; latency_ms: number; input: unknown; output: unknown; tool_calls: ToolCall[] | null };
type Execution = { id: string; success: boolean; error?: string; response: { simulated?: boolean } | null };
type RecoveryItem = { event_id: string; order_id?: string; subscription_id?: string; buyer_ref?: string | null; amount: string; currency: string };
type Proposal = {
  id: string;
  action: string;
  tier: string;
  status: string;
  rationale: string;
  params: { items?: RecoveryItem[]; total?: string; currency?: string } | null;
  executions?: Execution[];
};
type Money = {
  impact: string;
  requested: string;
  recovered: string;
  outstanding: string;
  currency: string;
  simulated: boolean;
  counts: { impact: number; requested: number; recovered: number };
};

function cash(value: string | undefined, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(value || 0));
}
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
  money?: Money;
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
    window.addEventListener("flatline-sse", on);
    return () => window.removeEventListener("flatline-sse", on);
  }, [refresh]);

  async function decide(proposalId: string, kind: "approve" | "reject") {
    // Show the decision at once; the server confirms it (and the execution) next.
    const status = kind === "approve" ? "approved" : "rejected";
    setRow((r) => (r ? { ...r, proposals: (r.proposals || []).map((p) => (p.id === proposalId ? { ...p, status } : p)) } : r));
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
      {row.money && row.money.counts.impact > 0 && (
        <div className="card money-line">
          <div>
            <div className="label">Lost</div>
            <strong>{cash(row.money.impact, row.money.currency)}</strong>
            <span className="muted"> · {row.money.counts.impact} sales</span>
          </div>
          <div>
            <div className="label">Asked back</div>
            <strong>{cash(row.money.requested, row.money.currency)}</strong>
            <span className="muted"> · {row.money.counts.requested} customers</span>
          </div>
          <div>
            <div className="label">Recovered</div>
            <strong className={Number(row.money.recovered) ? "ok-text" : ""}>{cash(row.money.recovered, row.money.currency)}</strong>
            {row.money.simulated && <span className="badge simulated" style={{ marginLeft: "0.4rem" }}>simulated</span>}
          </div>
        </div>
      )}
      <h2>Proposals</h2>
      {!(row.proposals || []).length && <p className="muted">No proposals yet. The agents are still working.</p>}
      {(row.proposals || []).map((p) => (
        <div className="card" key={p.id} style={{ marginBottom: "0.7rem" }}>
          <div className="proposal-head">
            <code>{p.action}</code>
            <span className={`badge ${p.tier}`}>{p.tier}</span>
            <span className={`badge ${p.status}`}>{p.status}</span>
            {p.rationale.startsWith("Red-team probe") && <span className="badge info">red-team probe</span>}
            {p.action.startsWith("recovery.") && <span className="badge info">planned by code, no model</span>}
          </div>
          <p style={{ color: "var(--pp-ink-2)" }}>{p.rationale}</p>
          {p.action.startsWith("recovery.") && (p.params?.items || []).length > 0 && (
            <table className="items">
              <thead>
                <tr><th>{p.action.includes("renewals") ? "Subscription" : "Order"}</th><th>Customer</th><th>Amount</th></tr>
              </thead>
              <tbody>
                {(p.params?.items || []).map((i) => (
                  <tr key={i.event_id}>
                    <td className="mono">{i.order_id || i.subscription_id}</td>
                    <td className="mono">{i.buyer_ref || "from the PayPal order"}</td>
                    <td>{cash(i.amount, i.currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {p.status === "pending" && (
            <div className="proposal-actions">
              <button onClick={() => void decide(p.id, "approve")}>
                {p.action.startsWith("recovery.")
                  ? `Approve: ask ${(p.params?.items || []).length} customers for ${cash(p.params?.total, p.params?.currency)}`
                  : "Approve"}
              </button>
              <button className="danger" onClick={() => void decide(p.id, "reject")}>Reject</button>
            </div>
          )}
          {(p.executions || []).map((e) => (
            <details key={e.id}>
              <summary>
                Execution <span className={`badge ${e.success ? "executed" : "failed"}`}>{e.success ? "success" : "failed"}</span>
                {e.response?.simulated && <span className="badge simulated" style={{ marginLeft: "0.4rem" }}>simulated, nothing sent to PayPal</span>}
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
            {(s.tool_calls || []).filter((c) => c.via).map((c, i) => (
              <span key={i} className="paypal-read">
                <span className="badge info">PayPal {c.via === "mcp" ? "MCP" : "REST"}</span>
                <code>{c.tool.replace(/^paypal\./, "")}</code>
                {c.result && <span className="muted">→ {c.result}</span>}
              </span>
            ))}
          </summary>
          <pre>{JSON.stringify({ input: s.input, output: s.output, tool_calls: s.tool_calls }, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
