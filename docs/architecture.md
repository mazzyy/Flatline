# Architecture

Flatline is an on-call SRE for a merchant's PayPal revenue.

```
 Demo shop ──(orders, subscriptions)──▶ PayPal sandbox ──(webhooks)──┐
     │                                                                 ▼
     └──────────────(checkout telemetry)────────────────────▶ Ingest (FastAPI)
                                                                       │
                                                                  Detector
                                                                       │
 PayPal MCP (READ) ──evidence──▶ Triage → Diagnostician → Remediator → Verifier
                                                                       │
 Dashboard (approve/reject) ─────────────────────────────────▶ Policy proxy
                                                                       │
                                                   Executor (WRITE MCP / REST)
                                                                       │
                                     resolved ──▶ Recovery planner (code, no model)
                                                   └─ one proposal back to the Policy proxy
```

## Recovery and the money ledger

When the verifier resolves an incident, `loop.settle_incident` runs the recovery planner. It writes one `impact` line to the money ledger (what the incident cost) and, when there are lost sales worth asking back, files one proposal through the policy proxy with `source="planner"`. After approval the executor reads each failed event again, creates and sends a PayPal invoice per customer (or retries each failed renewal) and writes a `requested` line per customer. A `recovered` line follows when PayPal reports the payment: `INVOICING.INVOICE.PAID` for an invoice, `PAYMENT.SALE.COMPLETED` for a renewal. Refunds the executor sends are written as `refunded` lines, and the daily refund budget is the sum of those over the last 24 hours.

The recovery proposal does not change the incident's status: the incident stays resolved, and approving a recovery does not run the verifier again.

## Why webhooks, not Transaction Search

PayPal Transaction Search can lag by up to three hours. Minute-level detection uses **webhooks + shop telemetry only**. Transaction Search (via `list_transactions`) is evidence and a stretch reconciliation input, never the detector's clock.

## Safety model

1. Every process refuses to start unless `PAYPAL_ENVIRONMENT` is `MOCK` or `SANDBOX`. There is no live PayPal host string.
2. Agent processes receive a `ReadOnlyGateway`. Write methods raise.
3. The remediator only *proposes* catalog actions. `flatline/policy/proxy.py` is plain code.
4. Only `flatline/policy/executor.py` calls PayPal write methods or mutates shop config.
5. Every detection, step, decision, approval and execution writes `audit_log`.
6. Money limits live in the proxy: a cap per refund, a daily refund budget (checked again by the executor at the moment of sending) and caps on a recovery. No refund is automatic unless `AUTO_REFUND_MAX` is set.
7. Recovery is planned by code. The proxy refuses a recovery action from an agent, the executor bills the amount on the failed event, and the payer's email is read from the PayPal order only at send time.

## Components

| Process | Role |
| --- | --- |
| `flatline.ingest.app` | Webhooks, telemetry, dashboard API, SSE, static dashboard |
| `flatline.detector.worker` | 30s scan, baselines, incidents, agent jobs |
| `flatline.loop` | Agents + proxy + executor + verifier, then the recovery planner |
| `flatline.recovery` | Recovery planner and money ledger (library code, no process of its own) |
| `flatline.bench` | Scored benchmark, in process, always on the mock gateway |
| `demo-shop` | Lumen Coffee Co. (MOCK pay or JS SDK v6) |

Docker Compose runs the three Python processes separately. On Render, one free web service runs all of them (`RUN_WORKERS=true` starts the detector and the agent loop as threads inside the API).

Storage is PostgreSQL 16 in Docker/Render. Tests use SQLite.

## Models

Every agent calls a model through LiteLLM. `MODEL_FAST` serves Triage and Verifier, `MODEL_REASONING` serves Diagnostician and Remediator, and `MODEL_FALLBACKS` lists models to try when one is rate limited. The hosted demo uses Gemini; a local model such as Qwen through Ollama works the same way. A step is always labelled with the model that actually answered, or as a playbook fallback.
