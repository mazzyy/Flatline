# Warden for Payments — Build Specification

> An on-call SRE agent for a merchant's revenue. It watches a PayPal integration, detects revenue incidents within minutes, diagnoses the root cause, and fixes them inside strict, deterministic guardrails, with every step audited.

This file is the single source of truth for the build. If anything here conflicts with an instinct or a framework default, this file wins. If something is unspecified, make the simplest reasonable choice and record it in `DECISIONS.md`.

- **Event:** PayPal AI Hackathon (Devpost). Deadline **Nov 12, 2026, 12:00 PST**.
- **Owner:** Sain (GitHub: `mazzyy`).
- **License:** MIT.
- **Environment:** PayPal **sandbox only**. Live mode must be impossible to enable by accident.

---

## 0. How to use this document (for the coding agent)

1. Read this whole file before writing code.
2. Build milestone by milestone (Section 14). Do not start a milestone until the previous one's acceptance criteria pass.
3. Everything must run and be testable **without any secrets**, using mock modes (Section 7). Real PayPal sandbox and real LLMs are switched on by env vars.
4. Never ask the owner questions. Decide, record the decision in `DECISIONS.md`, and keep going.
5. Keep `PROGRESS.md` current: one line per milestone with status, date and commit SHA.

---

## 1. Product summary

**Problem.** Small and mid-size merchants monitor servers, not money. A failing checkout, a webhook endpoint that silently returns 500, a wave of refunds from a bad product batch, or broken subscription renewals are usually noticed days later. Nobody is on call for revenue.

**Users.** E-commerce shops and SaaS founders using PayPal Checkout and Subscriptions without a payments team.

**What it does.** Detect → Diagnose → Propose → Gate → Execute → Verify, on three incident types (plus one stretch):

| Playbook | Detects | Typical fix |
| --- | --- | --- |
| `checkout_failure_spike` | Capture failures far above baseline | Roll back the bad shop config; banner; alert with root cause |
| `subscription_renewal_failures` | Failed renewals clustered on one plan or subscriber | Reminder; retry outstanding balance; pause sign-ups on a broken plan |
| `refund_wave` | Refunds far above baseline or concentrated on one product | Report; pause sales of that product |
| `webhook_gap` (stretch) | Transactions with no matching webhook | Replay missing events |

**Core safety principle (from Warden).** LLM agents never hold write credentials. Agents only *propose* actions. A deterministic policy proxy (plain code, not a prompt) classifies each proposal as `auto`, `approval` or `forbidden`. Only the Executor, behind the proxy, can write to PayPal.

---

## 2. Hackathon requirements this build must satisfy

- Meaningful use of PayPal developer platform (sandbox) **and** AI.
- Working prototype: hosted demo URL **and** clear local run instructions.
- Public repo, MIT `LICENSE` at root.
- `README.md` that lets a judge run it from a fresh clone.
- Demo video < 3 minutes (owner records it; you provide `docs/DEMO_SCRIPT.md`).
- Devpost text (you draft `docs/DEVPOST.md`), including which AI tools/models are used and how.

---

## 3. Non-negotiable rules

1. **Sandbox guard.** On startup every service checks `PAYPAL_ENVIRONMENT`. Any value other than `SANDBOX` (or `MOCK`) → refuse to start with a clear error. There is no code path to live PayPal endpoints.
2. **No write credentials in agent processes.** The agent workflow process only gets the read-scoped PayPal MCP server. Write tools exist only in the Executor.
3. **Allowlist policy.** Any action not in the action catalog (Section 9.6) is `forbidden` by default.
4. **No secrets in git.** `.env` is gitignored; `.env.example` lists every variable with a safe placeholder. Add a CI step that fails if a string resembling a secret is committed (e.g. `gitleaks` or a simple regex check).
5. **Everything audited.** Every detection, agent step, proposal, policy decision, approval and execution writes an `audit_log` row.
6. **Deterministic tests.** CI runs entirely in mock mode (no network, no keys).
7. **Synthetic data is labeled.** Any event not genuinely sent by PayPal is stored with `synthetic = true` and shown with a "simulated" badge in the UI.

---

## 4. Architecture

```
 Demo shop ──(orders, subscriptions)──▶ PayPal sandbox ──(webhooks)──┐
     │                                                                 ▼
     └──────────────(checkout telemetry)────────────────────▶ Ingest (FastAPI)
                                                                       │ events → Postgres
                                                                       ▼
                                                                  Detector (30 s loop)
                                                                       │ incident
                                                                       ▼
 PayPal MCP (READ scope) ──evidence──▶ Agent workflow: Triage → Diagnostician → Remediator → Verifier
                                                                       │ proposals
                                                                       ▼
 Dashboard (approve/reject) ─────────────────────────────────▶ Policy proxy (deterministic)
                                                                       │ allowed actions
                                                                       ▼
                                                   Executor: PayPal MCP (WRITE scope) + Subscriptions REST
                                                                       │
                                                                       ▼
                                                     PayPal sandbox / shop config / notifications
```

Real-time detection uses **webhooks + shop telemetry only**. PayPal Transaction Search can lag by up to three hours, so it is used only for reconciliation (stretch playbook) and evidence, never for minute-level detection.

---

## 5. Tech stack (fixed choices)

| Layer | Choice |
| --- | --- |
| Agents | Python 3.12, **Google ADK** (`google-adk`), models via **LiteLLM** (`google.adk.models.lite_llm.LiteLlm`) |
| Models | Configurable LiteLLM model strings. Owner uses **Azure** (Azure OpenAI GPT and Claude on Azure). No Gemini. |
| PayPal tools | `@paypal/mcp` (Node, run via `npx`) over stdio, **two instances**: read scope and write scope |
| PayPal REST | Thin `httpx` client for endpoints not covered by MCP (subscription suspend/activate/capture, webhook signature verification, token) |
| API / ingest | FastAPI + Uvicorn, SQLAlchemy 2.x, Alembic migrations |
| Detector | Python worker (asyncio loop), SQL aggregations |
| Storage | PostgreSQL 16 (SQLite allowed only for unit tests) |
| Dashboard | React + Vite + TypeScript, **AG Grid Community**, Server-Sent Events for live updates |
| Demo shop | Node 20 + Express, PayPal JS SDK v6 (fall back to v5 buttons only if v6 blocks you; record in `DECISIONS.md`) |
| Packaging | Docker per service, `docker-compose.yml` for local, `render.yaml` Blueprint for hosting |
| CI | GitHub Actions: lint (ruff, eslint), type check (mypy on `warden/`, tsc), tests, secret scan |

If Google ADK + LiteLLM + MCP integration hits a blocking bug, implement the four nodes as plain async Python using `litellm` and the `mcp` Python client, keeping the same node interfaces. Record it in `DECISIONS.md`.

---

## 6. Repository layout

```
warden-pay/
├── warden/                      # Python package (agents, policy, executor, ingest, detector share models)
│   ├── config.py                # env loading + sandbox guard
│   ├── db/                      # SQLAlchemy models, session, Alembic env
│   ├── paypal/
│   │   ├── gateway.py           # PayPalGateway protocol
│   │   ├── mock_gateway.py      # deterministic fixtures-backed implementation
│   │   ├── sandbox_gateway.py   # real sandbox via REST + MCP
│   │   ├── token.py             # OAuth token manager with refresh
│   │   ├── mcp_pool.py          # spawns/re-spawns read & write MCP servers
│   │   └── webhooks.py          # signature verification + event normalization
│   ├── llm/
│   │   ├── models.py            # LiteLLM model resolution from env
│   │   └── mock_llm.py          # deterministic stub used when LLM_MODE=mock
│   ├── agents/
│   │   ├── workflow.py          # ADK workflow wiring
│   │   ├── triage.py
│   │   ├── diagnostician.py
│   │   ├── remediator.py
│   │   ├── verifier.py
│   │   ├── schemas.py           # pydantic I/O for every node
│   │   └── prompts/             # one .md prompt per node
│   ├── playbooks/               # YAML playbook definitions + loader
│   ├── detector/                # rules, baselines, worker entrypoint
│   ├── policy/
│   │   ├── catalog.py           # action catalog with tiers
│   │   ├── proxy.py             # decide(), request_approval(), audit
│   │   └── executor.py          # performs allowed actions
│   ├── ingest/                  # FastAPI app: webhooks, telemetry, dashboard API, SSE
│   └── notify/                  # alert sinks: log, optional Telegram/Slack webhook
├── demo-shop/                   # Express app + chaos flags + telemetry
├── dashboard/                   # React + Vite + AG Grid
├── scripts/
│   ├── seed.py                  # baseline traffic generator
│   ├── inject.py                # fault injection per playbook
│   └── replay.py                # replay events
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/test_demo_scenarios.py
├── docs/
│   ├── architecture.md
│   ├── playbooks.md
│   ├── DEMO_SCRIPT.md
│   └── DEVPOST.md
├── fixtures/paypal/             # webhook payloads, API responses (sanitized sandbox shapes)
├── docker-compose.yml
├── render.yaml
├── Makefile
├── .env.example
├── .github/workflows/ci.yml
├── DECISIONS.md
├── PROGRESS.md
├── LICENSE                      # MIT, copyright 2026 Abdul Musawar Soomro
└── README.md
```

---

## 7. Configuration (`.env.example`)

```
# --- Modes ---
PAYPAL_ENVIRONMENT=MOCK          # MOCK | SANDBOX  (anything else = refuse to start)
LLM_MODE=mock                    # mock | live
APP_BASE_URL=http://localhost:8000

# --- PayPal sandbox ---
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=               # from the sandbox webhook registration
PAYPAL_SANDBOX_PLAN_ID=          # monthly plan used by the demo shop
PAYPAL_SANDBOX_PRODUCT_ID=

# --- Models (LiteLLM model strings) ---
MODEL_FAST=azure/<gpt-deployment-name>          # Triage, Verifier
MODEL_REASONING=azure/<gpt-or-claude-deployment> # Diagnostician, Remediator
AZURE_API_KEY=
AZURE_API_BASE=
AZURE_API_VERSION=
# If Claude is served via Azure AI Foundry, use the matching LiteLLM provider prefix and its env vars.

# --- Storage ---
DATABASE_URL=postgresql+psycopg://warden:warden@localhost:5432/warden

# --- Policy ---
REFUND_APPROVAL_MAX=50.00        # single refunds above this are forbidden for agents
AUTO_ACTIONS_ENABLED=true

# --- Dashboard ---
DASHBOARD_PASSCODE=demo-judge    # shared passcode for the hosted demo
INJECT_TOKEN=change-me           # protects synthetic-event and chaos endpoints

# --- Optional ---
GITHUB_TOKEN=                    # if set, config rollbacks also open a PR
GITHUB_REPO=mazzyy/warden-pay
NOTIFY_WEBHOOK_URL=              # Slack/Telegram/ntfy webhook for alerts
```

`warden/config.py` must load these with pydantic-settings, apply the sandbox guard, and expose `is_mock_paypal`, `is_mock_llm`.

---

## 8. Data model (Postgres)

All tables have `id` (UUID), `created_at` (timestamptz). Use Alembic for migrations.

| Table | Key columns |
| --- | --- |
| `events` | `source` (`paypal_webhook` / `shop_telemetry` / `synthetic`), `event_type`, `occurred_at`, `resource_id`, `amount`, `currency`, `product_id`, `plan_id`, `subscription_id`, `buyer_ref`, `error_code`, `payload` (jsonb), `synthetic` (bool), `verified` (bool). Unique on PayPal event id when present (idempotent ingest). |
| `shop_config_versions` | `version` (int), `config` (jsonb), `author` (`human` / `warden`), `active` (bool), `note` |
| `incidents` | `playbook`, `status` (`open` / `diagnosing` / `awaiting_approval` / `remediating` / `verifying` / `resolved` / `reopened` / `escalated`), `severity`, `metric`, `observed_value`, `baseline_value`, `window_start`, `window_end`, `revenue_at_risk_per_hour`, `title`, `root_cause` (text), `evidence` (jsonb), `resolved_at` |
| `agent_steps` | `incident_id`, `node` (`triage`/`diagnostician`/`remediator`/`verifier`), `input` (jsonb), `output` (jsonb), `model`, `latency_ms`, `tool_calls` (jsonb) |
| `proposals` | `incident_id`, `action` (catalog key), `params` (jsonb), `rationale`, `tier` (`auto`/`approval`/`forbidden`), `status` (`pending`/`approved`/`rejected`/`executed`/`failed`/`refused`), `decided_by`, `decided_at` |
| `executions` | `proposal_id`, `request` (jsonb), `response` (jsonb), `success` (bool), `error` |
| `audit_log` | `actor` (`detector`/`agent:<node>`/`policy`/`executor`/`human`), `action`, `incident_id`, `proposal_id`, `details` (jsonb) |

---

## 9. Component specifications

### 9.1 Demo shop (`demo-shop/`)

A small fictional store, **"Lumen Coffee Co."** (invented brand, no real company).

- Products: 3 coffee bags (one-off checkout) + "Coffee Club" monthly subscription using `PAYPAL_SANDBOX_PLAN_ID`.
- Pages: catalog, product, checkout (PayPal buttons), subscription signup, thank-you.
- Server routes: `POST /api/orders` (create), `POST /api/orders/:id/capture`, `GET /api/config`.
- Reads its active config from the Warden API (`GET /api/shop/config`), cached 10 s. Config keys: `currency`, `paused_products[]`, `plan_signups_paused`, `banner`, `chaos` (see below).
- **Chaos flags** (set from the dashboard chaos panel, stored in config):
  - `chaos.mock_response`: when set (e.g. `INSTRUMENT_DECLINED`, `INTERNAL_SERVER_ERROR`), the shop sends `PayPal-Mock-Response: {"mock_application_codes": "<code>"}` on capture calls (sandbox negative testing).
  - `chaos.bad_currency`: when true, the shop creates orders with a mismatched currency, causing failures. This is the "bad deploy" a config rollback fixes.
- **Telemetry:** after every create/capture attempt, `POST {WARDEN}/api/telemetry` with `{type: "checkout.create"|"checkout.capture", ok, error_code, order_id, amount, currency, product_id, latency_ms, at}`.
- In `PAYPAL_ENVIRONMENT=MOCK` the shop uses a mock PayPal (no buttons; a "Pay (mock)" button that hits the server, which simulates success/failure per chaos flags).
- Shows `banner` text at the top when set.

### 9.2 Ingest and API (`warden/ingest/`)

FastAPI app. Endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/webhooks/paypal` | Receive PayPal webhooks; verify signature via PayPal verify-webhook-signature API (sandbox) or skip in MOCK; normalize; store idempotently |
| POST | `/api/telemetry` | Shop telemetry |
| POST | `/api/synthetic/events` | Synthetic events for demo/injection. Requires `X-Inject-Token`. Stored with `synthetic=true` |
| GET | `/api/shop/config` | Active shop config (public, read-only) |
| GET | `/api/incidents` | List with filters |
| GET | `/api/incidents/{id}` | Incident + agent steps + proposals + executions |
| POST | `/api/proposals/{id}/approve` | Human approval (passcode auth) |
| POST | `/api/proposals/{id}/reject` | Human rejection |
| GET | `/api/events` | Paginated events for AG Grid (server-side filtering/sorting) |
| GET | `/api/metrics/health` | Current revenue health score + per-metric status |
| GET | `/api/audit` | Audit log |
| POST | `/api/chaos` | Set chaos flags (passcode + inject token) |
| GET | `/api/stream` | SSE: `incident.created`, `incident.updated`, `step.added`, `proposal.created`, `proposal.updated`, `event.ingested` |
| GET | `/healthz` | Liveness |

Webhook event types to subscribe and normalize: `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.DENIED`, `PAYMENT.CAPTURE.REFUNDED`, `CHECKOUT.ORDER.APPROVED`, `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.PAYMENT.FAILED`, `BILLING.SUBSCRIPTION.SUSPENDED`, `BILLING.SUBSCRIPTION.CANCELLED`, `CUSTOMER.DISPUTE.CREATED`. Unknown types are stored but ignored by detectors.

### 9.3 Detector (`warden/detector/`)

- Runs every 30 s. For each enabled playbook, computes its metric over the current window and a baseline.
- Baseline: mean of the metric over the previous 12 windows (excluding current), floored at a per-playbook minimum so tiny baselines do not trigger on noise.
- Breach: `current >= multiplier × baseline` **and** `count >= min_count` (values per playbook in Section 10).
- On breach, if no open incident exists for the same playbook + scope key (e.g. plan id, product id), create one, compute `revenue_at_risk_per_hour` (lost captures × average order value, or failed renewals × plan price), emit SSE, enqueue agent workflow.
- Dedupe: same playbook + scope within 30 min updates the existing incident instead of creating a new one.

### 9.4 PayPal layer (`warden/paypal/`)

- `PayPalGateway` protocol with read methods (`list_transactions`, `get_order`, `get_refund`, `get_subscription`, `get_plan`, `list_disputes`, `get_dispute`, `get_merchant_insights`) and write methods (`create_refund`, `suspend_subscription`, `activate_subscription`, `capture_subscription_outstanding`, `send_invoice_reminder`, `create_invoice`, `send_invoice`).
- `MockGateway`: deterministic, backed by `fixtures/paypal/` and the local DB.
- `SandboxGateway`: read methods via the **read-scoped MCP server**; write methods via the **write-scoped MCP server** or REST where MCP lacks the call (subscription suspend/activate/capture).
- `token.py`: client-credentials OAuth against `https://api-m.sandbox.paypal.com/v1/oauth2/token`; cache; refresh 15 min before expiry (tokens live a few hours).
- `mcp_pool.py`: spawns `npx -y @paypal/mcp` with `PAYPAL_ENVIRONMENT=SANDBOX`, `PAYPAL_ACCESS_TOKEN=<token>`, and:
  - read instance: `--tools=transactions.list,orders.get,payments.getRefunds,subscriptions.show,subscriptionPlans.show,subscriptionPlans.list,disputes.list,disputes.get,invoices.list,invoices.get`
  - write instance: `--tools=payments.createRefund,invoices.create,invoices.send,invoices.sendReminder`
  - Respawn both when the token refreshes. Verify actual tool identifiers against the `@paypal/mcp` README at build time and adjust; record any difference in `DECISIONS.md`.
- Only `warden/policy/executor.py` may import the write side. Add a test that fails if any module under `warden/agents/` imports write methods or the write MCP instance.

### 9.5 Agent workflow (`warden/agents/`)

Four nodes, each with pydantic input/output schemas, a prompt file, and a model from env. In `LLM_MODE=mock`, `mock_llm.py` returns deterministic, playbook-aware outputs so the whole pipeline is testable offline.

| Node | Model | Input | Output |
| --- | --- | --- | --- |
| Triage | `MODEL_FAST` | Incident row + last 50 related events | `{playbook_confirmed: bool, severity: low/med/high/critical, scope: {...}, revenue_at_risk_per_hour, summary}` |
| Diagnostician | `MODEL_REASONING` | Triage output + read-only PayPal tools + DB query tools (events by group, active config history) | `{root_cause, confidence 0–1, evidence: [{claim, source, ref}], hypotheses_rejected: [...]}` |
| Remediator | `MODEL_REASONING` | Diagnosis + playbook's allowed actions + catalog descriptions | `{proposals: [{action, params, rationale, expected_effect}]}` — may only use catalog actions |
| Verifier | `MODEL_FAST` + deterministic metric check | Incident metric after fix | `{resolved: bool, observation, next_step}` |

Rules:
- The Diagnostician must cite evidence for every claim (event ids, order ids, config version). Unsupported claims fail schema validation and trigger one retry.
- The Remediator's proposals go to the policy proxy; the agent never calls the executor.
- The Verifier's resolution decision is **deterministic**: metric under threshold for `verify_minutes` (default 10; 1 in demo mode via `VERIFY_MINUTES`). The LLM only writes the narrative.
- If the proxy refuses a proposal (`forbidden`), the incident gets an `escalated` note with the agent's written recommendation for a human.
- Every node run writes `agent_steps` and `audit_log` rows and emits SSE.

### 9.6 Policy proxy and executor (`warden/policy/`)

Action catalog (allowlist). Anything else is `forbidden`.

| Action key | Tier | Notes |
| --- | --- | --- |
| `notify.alert` | auto | Log + optional `NOTIFY_WEBHOOK_URL` |
| `report.create` | auto | Attach markdown report to incident |
| `shop.banner.set` / `shop.banner.clear` | auto | New config version |
| `invoice.send_reminder` | auto | To one subscriber |
| `shop.config.rollback` | approval | Activate a previous config version; if `GITHUB_TOKEN` set, also open a PR documenting it |
| `shop.product.pause_sales` / `resume_sales` | approval | Config change |
| `shop.plan.pause_signups` / `resume_signups` | approval | Config change |
| `subscription.capture_outstanding` | approval | REST |
| `subscription.suspend` / `subscription.activate` | approval | REST, one subscription per proposal |
| `refund.single` | approval | Only if amount ≤ `REFUND_APPROVAL_MAX`; otherwise `forbidden` |
| `events.replay` | approval | Stretch playbook |
| `refund.bulk`, `subscription.cancel*`, `dispute.accept*`, `payout.*`, `credentials.*`, `webhook.delete*` | forbidden | Explicitly listed to show in the UI |

- `proxy.decide(proposal) -> tier` is pure, unit-tested code with no LLM.
- `auto` → executed immediately; `approval` → `pending` until a human approves in the dashboard; `forbidden` → `refused` + escalation note.
- Rate limits: max 5 auto actions per incident; max 1 pending approval per action key per incident.
- Executor performs the action, writes `executions` + `audit_log`, then triggers the Verifier.

### 9.7 Dashboard (`dashboard/`)

Passcode login (`DASHBOARD_PASSCODE`). Pages:

1. **Overview:** revenue health score, live metric tiles per playbook (current vs baseline), live incident feed via SSE.
2. **Incident detail:** timeline of agent steps (expandable inputs/outputs and tool calls), root-cause card with evidence links, proposals with tier badges and Approve/Reject buttons, executions, verification result.
3. **Transactions:** AG Grid over `/api/events` with server-side sorting, filtering, quick filter, column groups, and a "simulated" badge renderer. This page should be good enough to compete for the AG Grid prize.
4. **Policy:** read-only view of the action catalog and tiers.
5. **Audit log:** AG Grid, filterable by incident and actor.
6. **Chaos panel:** buttons: "Inject checkout failures (declines)", "Inject checkout failures (server errors)", "Ship bad currency config", "Inject refund wave", "Inject subscription renewal failures", "Break webhook endpoint (stretch)", "Reset all chaos".

Visual style: clean, light/dark, readable at 125% zoom for video recording.

### 9.8 Scripts

- `scripts/seed.py`: generates steady baseline traffic for N minutes. In SANDBOX, create and capture real orders where possible (use the PayPal-documented sandbox test-card approach or buyer flows; if server-side capture without buyer approval is not possible, generate shop telemetry plus synthetic events and record this in `DECISIONS.md`). In MOCK, generate realistic synthetic events.
- `scripts/inject.py <playbook>`: triggers each fault (sets chaos flags, performs refunds of recent sandbox captures for one product, or posts synthetic failed-renewal events marked `synthetic=true`).
- `scripts/replay.py`: replay stored events into the detector for testing.

---

## 10. Playbooks (YAML in `warden/playbooks/`)

Thresholds are starting values; expose them in YAML.

```yaml
checkout_failure_spike:
  metric: capture_failures            # from shop telemetry + PAYMENT.CAPTURE.DENIED
  window_minutes: 5
  multiplier: 3
  min_count: 5
  baseline_floor: 1
  scope_key: none
  evidence: [error_code_breakdown, distinct_buyers, active_config_diff, sample_orders]
  allowed_actions: [notify.alert, report.create, shop.banner.set, shop.config.rollback]

subscription_renewal_failures:
  metric: renewal_failures            # BILLING.SUBSCRIPTION.PAYMENT.FAILED
  window_minutes: 60
  multiplier: 3
  min_count: 3
  baseline_floor: 0.5
  scope_key: plan_id
  evidence: [subscription_details, failures_per_subscriber, plan_details]
  allowed_actions: [notify.alert, report.create, invoice.send_reminder,
                    subscription.capture_outstanding, shop.plan.pause_signups]

refund_wave:
  metric: refunds                     # PAYMENT.CAPTURE.REFUNDED
  window_minutes: 60
  multiplier: 3
  min_count: 4
  baseline_floor: 1
  scope_key: product_id               # also trigger if >50% of refunds in window share one product
  evidence: [refunds_by_product, refunds_by_buyer, purchase_dates, linked_disputes]
  allowed_actions: [notify.alert, report.create, shop.product.pause_sales]

webhook_gap:                          # stretch
  metric: missing_webhooks
  reconcile_lag_hours: 3
  evidence: [missing_event_count, endpoint_error_log]
  allowed_actions: [notify.alert, events.replay]
```

Expected demo outcomes:
- **Checkout spike via bad currency:** root cause names the config version that introduced the wrong currency; proposal `shop.config.rollback` (approval) + `shop.banner.set` (auto); after approval, failures stop and Verifier resolves.
- **Checkout spike via mock declines:** root cause identifies buyer-side declines across many buyers; proposes alert + banner; no rollback.
- **Refund wave:** root cause names the product; proposes `shop.product.pause_sales` (approval). If the agent proposes `refund.bulk`, the proxy refuses it and the UI shows the refusal.
- **Renewal failures:** proposes `invoice.send_reminder` (auto) and `subscription.capture_outstanding` (approval).

---

## 11. Testing

- **Unit:** policy proxy decisions (every catalog key and unknown keys), baseline/breach math, webhook normalization, config sandbox guard, import-boundary test for write access.
- **Integration (mock):** ingest → detector → incident; workflow with `mock_llm`; approval → executor → verifier.
- **E2E (mock):** `tests/e2e/test_demo_scenarios.py` runs all three demo scenarios from Section 10 against docker-compose services (or in-process) and asserts the expected incident, root-cause keywords, proposal tiers and final status. `make demo-test` runs it.
- **Live smoke (optional, skipped without keys):** `make sandbox-smoke` checks token, MCP read tools respond, webhook verification works.
- CI must be green on every milestone commit.

---

## 12. Deployment

- `docker-compose.yml`: postgres, api (ingest + SSE), detector, agents (worker that consumes incident queue — a Postgres-backed queue table or `LISTEN/NOTIFY` is fine), dashboard (static build served by api or nginx), demo-shop. `make up` starts everything in MOCK mode with seeded data.
- The agents image needs **both Python and Node 20** (for `npx @paypal/mcp`).
- `render.yaml` Blueprint: web service `warden-api`, background workers `warden-detector` and `warden-agents`, web service `demo-shop`, static site or api-served `dashboard`, managed Postgres. Env vars referenced as `sync: false` secrets.
- README section "Deploy to Render" with the Blueprint button and the list of env vars to fill.

---

## 13. Documentation deliverables

- `README.md`: one-paragraph pitch, architecture image/diagram, quick start (`cp .env.example .env && make up`), sandbox setup steps (developer account, REST app, webhook registration, plan creation, enabling Transaction Search permission), how to run the demo scenarios, how the safety model works, tech/tools used, license.
- `docs/architecture.md`: components, data flow, safety model, why webhooks vs Transaction Search.
- `docs/playbooks.md`: each playbook in plain language.
- `docs/DEMO_SCRIPT.md`: a 2:50 video script (hook → normal traffic → checkout incident end to end → refund wave with refused bulk refund → renewal failures → architecture → close).
- `docs/DEVPOST.md`: Inspiration, What it does, How we built it, PayPal usage, AI usage (model per node and why), Challenges, Accomplishments, What's next, Built with.
- `DECISIONS.md`, `PROGRESS.md` kept current.

---

## 14. Milestones and acceptance criteria

Each milestone ends with: tests green, `PROGRESS.md` updated, one commit `M<n>: <summary>` pushed.

| # | Milestone | Acceptance criteria |
| --- | --- | --- |
| M0 | Scaffold | Layout from Section 6; MIT LICENSE; `.env.example`; config with sandbox guard + tests; Makefile (`up`, `down`, `test`, `lint`, `demo-test`); CI workflow passing; empty `DECISIONS.md`/`PROGRESS.md` |
| M1 | PayPal layer | Gateway protocol, MockGateway with fixtures, SandboxGateway skeleton, token manager, MCP pool, webhook verification + normalization; unit tests; import-boundary test |
| M2 | Data + ingest | Alembic schema (Section 8); webhook, telemetry, synthetic endpoints; idempotent ingest; SSE stream; tests |
| M3 | Demo shop | Express shop working in MOCK; sandbox path implemented; chaos flags; telemetry; config fetch; Dockerfile |
| M4 | Detector | Playbook YAML loader; baselines; breach; dedupe; revenue at risk; incidents + SSE; tests with replayed fixtures |
| M5 | Agents part 1 | ADK workflow; Triage + Diagnostician with read tools and DB tools; mock LLM; evidence-required schema; `agent_steps` persisted; checkout-spike diagnosis test passes in mock |
| M6 | Policy + fix loop | Catalog, proxy, approvals API, executor, Remediator, deterministic Verifier; checkout-spike scenario fully end to end in mock |
| M7 | All playbooks | Renewal failures and refund wave end to end; refused bulk refund path; `make demo-test` green for all three |
| M8 | Dashboard | All pages in 9.7; live SSE updates; AG Grid server-side grids; chaos panel wired |
| M9 | Deploy + scripts | docker-compose full stack; `render.yaml`; seed/inject/replay scripts; sandbox smoke target |
| M10 | Docs | All documents in Section 13 complete and accurate |
| S1 | Stretch: webhook gap | Only if M0–M10 are complete |

---

## 15. Out of scope

Live mode, real money, onboarding other merchants, payouts, trained ML anomaly models, mobile apps, multi-tenant auth.
