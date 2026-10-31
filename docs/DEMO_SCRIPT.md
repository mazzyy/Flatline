# Demo script (~2:50)

Record at 125% zoom. Dark or light theme both work. Start with `cp .env.example .env && make up`.

**0:00–0:15 — Hook.**  
"Small shops monitor servers, not money. A silent checkout break is noticed days later. Flatline is on call for revenue."

**0:15–0:35 — Normal traffic.**  
Open the demo shop (localhost:3000). Buy House Blend with **Pay (mock)**. Thank-you page. Dashboard Overview: health score high, playbook tiles quiet. Transactions grid: the capture, no simulated badge.

**0:35–1:25 — Checkout incident.**  
Chaos panel → **Ship bad currency config**. Shop checkout now fails (`CURRENCY_MISMATCH`). Inject six failures (or `python scripts/inject.py checkout_failure_spike`). Wait for the detector (30s) or run `python scripts/replay.py`. Overview shows a checkout spike. Incident: Diagnostician names **config version N**. Banner is auto-set. Rollback is **approval**. Approve it. Failures stop. Verifier resolves.

**1:25–1:55 — Refund wave + refusal.**  
Chaos → **Inject refund wave**. Incident names Ethiopia Yirgacheffe. Pause-sales is approval. `refund.bulk` is **forbidden** — the UI shows the refusal. That is the safety model: the agent asked, the proxy said no.

**1:55–2:20 — Renewal failures.**  
Inject subscription renewal failures. Reminder is auto. Capture outstanding waits for approval.

**2:20–2:40 — Architecture.**  
Dashboard → **How it works** (the Detect→Verify loop, the three policy tiers and the judge walkthrough live there), or the README diagram. Agents are read-only. Only the executor writes, and only after the catalog proxy.

**2:40–2:50 — Close.**  
"Sandbox only. Every step audited. MIT. That's Flatline."
