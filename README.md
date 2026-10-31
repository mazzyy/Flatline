# Warden for Payments

An on-call SRE agent for a merchant's revenue. It watches a PayPal integration,
detects checkout failures, refund waves and broken subscription renewals within
minutes, diagnoses the root cause from evidence, and applies fixes only after a
**deterministic policy proxy** (plain code, not a prompt) allows them.

Built for the PayPal AI Hackathon. MIT. Copyright 2026 Abdul Musawar Soomro.

Agents never hold write credentials. Only the Executor writes to PayPal or shop
config, and only after the catalog says `auto` or a human approves.

```
Demo shop → PayPal sandbox / mock → webhooks + telemetry → Detector
        → Triage → Diagnostician → Remediator → Policy proxy → Executor → Verifier
```

See [docs/architecture.md](docs/architecture.md).

## Quick start (no secrets)

```bash
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
make test
make demo-test
```

Full stack in mock mode (Docker):

```bash
cp .env.example .env
make up
```

- API + dashboard: http://localhost:8000  (passcode `demo-judge`)
- Demo shop: http://localhost:3000
- Stop: `make down`

`PAYPAL_ENVIRONMENT` must be `MOCK` or `SANDBOX`. Any other value refuses to start. There is no live PayPal path.

## Demo scenarios

With the stack up:

```bash
python scripts/seed.py --minutes 10
python scripts/inject.py checkout_failure_spike
# wait ~30s for the detector, or:
python scripts/replay.py
```

Or use the dashboard **Chaos** panel. Expected outcomes are in [docs/playbooks.md](docs/playbooks.md) and the [demo script](docs/DEMO_SCRIPT.md).

Synthetic events show a **simulated** badge on the Transactions grid.

## Sandbox setup (owner)

1. Create a [PayPal Developer](https://developer.paypal.com/) sandbox app (REST).
2. Copy Client ID / Secret into `.env`. Keep `PAYPAL_ENVIRONMENT=SANDBOX`.
3. Enable **Transaction Search** on the app (evidence only; not used for minute-level detection).
4. Register a webhook on `https://<your-api>/webhooks/paypal` for the event types in SPEC §9.2. Put the webhook ID in `PAYPAL_WEBHOOK_ID`.
5. Create a catalog product and a monthly **Coffee Club** plan; set `PAYPAL_SANDBOX_PLAN_ID` and `PAYPAL_SANDBOX_PRODUCT_ID`.
6. For live models: Azure OpenAI (or Claude on Azure AI Foundry) keys and LiteLLM model strings in `MODEL_FAST` / `MODEL_REASONING`. Then `pip install -r requirements-live.txt` and `LLM_MODE=live`.
7. Point the demo shop at the same client id so JS SDK v6 buttons render.

Tests never require these keys.

## Deploy to Render

This repo includes a [Blueprint](render.yaml).

1. New → Blueprint → this repo.
2. Fill the `sync: false` env vars: PayPal sandbox credentials, webhook id, plan id, Azure keys, `DASHBOARD_PASSCODE`, `INJECT_TOKEN`, `APP_BASE_URL`, `WARDEN_API_URL` for the shop.
3. `PAYPAL_ENVIRONMENT` is set to `SANDBOX` in the Blueprint. Do not set it to live.

## Safety model

| Rule | Enforcement |
| --- | --- |
| No live PayPal | Startup guard + no live host string |
| Agents are read-only | `ReadOnlyGateway` + import-boundary test |
| Unknown actions forbidden | `warden/policy/catalog.py` allowlist |
| Writes only after policy | `executor.py` is the only writer |
| Everything audited | `audit_log` rows + SSE |

## Tech

Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Google ADK + LiteLLM (live), `@paypal/mcp`, PayPal REST + JS SDK v6, React, Vite, TypeScript, AG Grid Community, Docker, PostgreSQL 16.

## License

MIT. See `LICENSE`.
