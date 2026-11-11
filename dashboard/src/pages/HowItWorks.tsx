import { useSite } from "../site";

const STEPS: { title: string; who: "agent" | "code" | "human"; whoLabel: string; text: string }[] = [
  {
    title: "Detect",
    who: "code",
    whoLabel: "Deterministic",
    text: "Webhooks and shop telemetry land in Postgres. Every 30 seconds (and instantly after chaos) the detector compares the current window with a 12-window baseline per playbook.",
  },
  {
    title: "Diagnose",
    who: "agent",
    whoLabel: "Agents · read-only",
    text: "Triage and Diagnostician read events, config history and PayPal (read scope only). The root cause must cite evidence; the schema rejects claims without a source.",
  },
  {
    title: "Propose",
    who: "agent",
    whoLabel: "Agent · read-only",
    text: "The Remediator drafts actions from the playbook's allowlist, each with a rationale. It can only propose; it holds no write credentials.",
  },
  {
    title: "Gate",
    who: "code",
    whoLabel: "Policy proxy",
    text: "Plain code classifies every proposal as auto, approval or forbidden. Unknown actions are forbidden. Refunds above the cap are forbidden. Rate limits apply.",
  },
  {
    title: "Execute",
    who: "human",
    whoLabel: "You approve",
    text: "Auto actions run immediately. Approval actions wait for a human on the incident page. The Executor is the only component that writes to PayPal or shop config.",
  },
  {
    title: "Verify",
    who: "code",
    whoLabel: "Deterministic",
    text: "After the fix, the verifier watches the metric for a quiet window and resolves the incident, or reopens it. Every step is in the audit log.",
  },
  {
    title: "Recover",
    who: "human",
    whoLabel: "Code plans · you approve",
    text: "Once the incident is resolved, code reads the failed events and lists who lost a sale and for how much. One approval sends each of them a PayPal invoice, or retries each failed renewal. No model is involved, so no amount can be invented.",
  },
];

export default function HowItWorks() {
  const { shopUrl: SHOP_URL } = useSite();
  return (
    <div>
      <section className="hero">
        <h1>An on-call SRE for your PayPal revenue</h1>
        <p>
          Merchants monitor servers, not money. Flatline watches a PayPal integration, spots revenue incidents
          within minutes, explains the cause from evidence, fixes it inside strict guardrails, and then asks
          the lost sales back. AI proposes; deterministic code decides; only the Executor writes.
        </p>
        <div className="pills">
          <span className="pill">PayPal sandbox + MCP</span>
          <span className="pill">Four-node agent workflow</span>
          <span className="pill">Deterministic policy gate</span>
          <span className="pill">Human approval</span>
          <span className="pill">Full audit trail</span>
        </div>
      </section>

      <h2>The loop</h2>
      <div className="steps">
        {STEPS.map((s, i) => (
          <div className="card step" key={s.title}>
            <div className="n">{i + 1}</div>
            <div className={`who ${s.who}`}>{s.whoLabel}</div>
            <h3>{s.title}</h3>
            <p>{s.text}</p>
          </div>
        ))}
      </div>

      <h2>What it watches</h2>
      <div className="three">
        <div className="card">
          <h3>Checkout failure spike</h3>
          <p className="muted">Capture failures far above baseline in a 5-minute window.</p>
          <ul className="kv">
            <li><strong>Bad config shipped?</strong> Banner (auto) + roll back the shop config (approval).</li>
            <li><strong>Issuer declines across many buyers?</strong> Alert + banner. No rollback of a healthy config.</li>
          </ul>
        </div>
        <div className="card">
          <h3>Subscription renewal failures</h3>
          <p className="muted">Failed renewals clustered on one plan over 60 minutes.</p>
          <ul className="kv">
            <li><strong>Auto:</strong> send a payment reminder to each subscriber.</li>
            <li><strong>Approval:</strong> capture the outstanding balance; pause sign-ups on a broken plan.</li>
          </ul>
        </div>
        <div className="card">
          <h3>Refund wave</h3>
          <p className="muted">Refunds far above baseline or concentrated on one product.</p>
          <ul className="kv">
            <li><strong>Approval:</strong> pause sales of that product.</li>
            <li><strong>Forbidden:</strong> bulk refunds. The proxy refuses and escalates to a human with the written recommendation.</li>
          </ul>
        </div>
      </div>

      <h2>Who may do what</h2>
      <div className="three">
        <div className="card">
          <div className="tier-head"><h3>Auto</h3><span className="badge auto">runs immediately</span></div>
          <p className="muted">Low-risk, reversible. Alerts, reports, shop banner, one-subscriber reminders.</p>
        </div>
        <div className="card">
          <div className="tier-head"><h3>Approval</h3><span className="badge approval">waits for you</span></div>
          <p className="muted">Changes money or availability. Config rollback, pause a product or plan, capture a balance, a single refund under the cap, sending recovery invoices.</p>
        </div>
        <div className="card">
          <div className="tier-head"><h3>Forbidden</h3><span className="badge forbidden">never by agents</span></div>
          <p className="muted">Bulk refunds, cancellations, accepting disputes, payouts, credential or webhook changes. Anything not in the catalog.</p>
        </div>
      </div>
      <div className="note">
        Agent processes receive a read-only PayPal gateway. An import-boundary test fails the build if any agent
        module touches the write surface. The full allowlist is on the <a href="#/policy">Policy</a> page.
      </div>

      <h2>Try it in two minutes</h2>
      <div className="card">
        <ol className="walk">
          <li>
            <div>
              <strong>Open the demo shop</strong>
              <span>
                <a href={SHOP_URL} target="_blank" rel="noreferrer">{SHOP_URL}</a> — Lumen Coffee Co., a fictional roastery.
                Buy a bag with <em>Pay (mock)</em>. In sandbox mode the real PayPal button renders instead.
              </span>
            </div>
          </li>
          <li>
            <div>
              <strong>Break something</strong>
              <span>
                Go to <a href="#/chaos">Chaos</a> and click <em>Ship bad currency config</em> or <em>Inject checkout failures</em>.
                Synthetic events are stored with a <span className="badge simulated">simulated</span> badge.
              </span>
            </div>
          </li>
          <li>
            <div>
              <strong>Watch detection</strong>
              <span>The <a href="#/overview">Overview</a> flips a playbook tile to <em>breach</em> and lists a new incident with revenue at risk per hour.</span>
            </div>
          </li>
          <li>
            <div>
              <strong>Read the diagnosis</strong>
              <span>Open the incident. Root cause, cited evidence, the four agent steps with inputs and outputs, and each proposal with its policy tier.</span>
            </div>
          </li>
          <li>
            <div>
              <strong>Approve or reject</strong>
              <span>Auto actions have already run (for example the shop banner). Approve the rollback and the Executor activates the previous config version.</span>
            </div>
          </li>
          <li>
            <div>
              <strong>See it verified</strong>
              <span>The verifier watches a quiet window and marks the incident resolved. Reload the shop: the banner is gone and checkout works again.</span>
            </div>
          </li>
          <li>
            <div>
              <strong>Get the lost sales back</strong>
              <span>
                About a minute later a recovery proposal appears on the incident: the customers whose checkout failed, and what each tried to pay.
                Approve it, then click <em>Customers pay their recovery requests</em> in <a href="#/chaos">Chaos</a> and watch <em>Recovered</em> on the Overview.
              </span>
            </div>
          </li>
          <li>
            <div>
              <strong>Try the refusal</strong>
              <span>Inject a refund wave. The agent recommends a bulk refund; the proxy refuses it and escalates with the recommendation attached. Then check <a href="#/audit">Audit</a>.</span>
            </div>
          </li>
          <li>
            <div>
              <strong>Reset</strong>
              <span>Click <em>Reset all chaos</em> on the Chaos page to return the shop to a clean state.</span>
            </div>
          </li>
        </ol>
      </div>

      <h2>Modes and data</h2>
      <div className="three">
        <div className="card">
          <h3>MOCK</h3>
          <p className="muted">No keys, no network. PayPal responses come from fixtures and the agent nodes use a scripted mock model. This is what the tests and the hosted demo default to.</p>
        </div>
        <div className="card">
          <h3>SANDBOX</h3>
          <p className="muted">Real PayPal sandbox: JS SDK v6 checkout, verified webhooks, the official <code>@paypal/mcp</code> read tools, REST for subscription writes. Live LLMs via LiteLLM.</p>
        </div>
        <div className="card">
          <h3>Never live</h3>
          <p className="muted">Every process refuses to start unless <code>PAYPAL_ENVIRONMENT</code> is MOCK or SANDBOX. No live host string exists in the codebase.</p>
        </div>
      </div>
      <div className="note warn">
        Detection uses webhooks and shop telemetry, not PayPal Transaction Search, which can lag by hours. Transaction Search is used only as evidence.
      </div>
    </div>
  );
}
