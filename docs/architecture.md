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
3. The remediator only *proposes* catalog actions. `flatline/policy/proxy.py` is plain code.
4. Only `flatline/policy/executor.py` calls PayPal write methods or mutates shop config.
5. Every detection, step, decision, approval and execution writes `audit_log`.

## Components

| Process | Role |
| --- | --- |
| `flatline.ingest.app` | Webhooks, telemetry, dashboard API, SSE, static dashboard |
| `flatline.detector.worker` | 30s scan, baselines, incidents, agent jobs |
| `flatline.loop` | Agents + proxy + executor + verifier |
| `demo-shop` | Lumen Coffee Co. (MOCK pay or JS SDK v6) |

Docker Compose runs the three Python processes separately. On Render, one free web service runs all of them (`RUN_WORKERS=true` starts the detector and the agent loop as threads inside the API).

Storage is PostgreSQL 16 in Docker/Render. Tests use SQLite.

## Models

Every agent calls a model through LiteLLM. `MODEL_FAST` serves Triage and Verifier, `MODEL_REASONING` serves Diagnostician and Remediator, and `MODEL_FALLBACKS` lists models to try when one is rate limited. The hosted demo uses Gemini; a local model such as Qwen through Ollama works the same way. A step is always labelled with the model that actually answered, or as a playbook fallback.
