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
```

## Why webhooks, not Transaction Search

PayPal Transaction Search can lag by up to three hours. Minute-level detection uses **webhooks + shop telemetry only**. Transaction Search (via `list_transactions`) is evidence and a stretch reconciliation input, never the detector's clock.

## Safety model

1. Every process refuses to start unless `PAYPAL_ENVIRONMENT` is `MOCK` or `SANDBOX`. There is no live PayPal host string.
2. Agent processes receive a `ReadOnlyGateway`. Write methods raise.
3. The remediator only *proposes* catalog actions. `warden/policy/proxy.py` is plain code.
4. Only `warden/policy/executor.py` calls PayPal write methods or mutates shop config.
5. Every detection, step, decision, approval and execution writes `audit_log`.

## Components

| Process | Role |
| --- | --- |
| `warden.ingest.app` | Webhooks, telemetry, dashboard API, SSE, static dashboard |
| `warden.detector.worker` | 30s scan, baselines, incidents, agent jobs |
| `warden.loop` | Agents + proxy + executor + verifier |
| `demo-shop` | Lumen Coffee Co. (MOCK pay or JS SDK v6) |

Storage is PostgreSQL 16 in Docker/Render. Tests use SQLite.
