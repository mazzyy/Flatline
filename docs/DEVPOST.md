# Devpost draft

## Inspiration

The original Warden project put SRE agents on a Kubernetes estate and refused to give them write credentials. Payments have the same shape of problem: a checkout 500, a refund wave, a broken plan, and nobody is on call for revenue.

## What it does

Warden for Payments watches a merchant PayPal integration (Checkout + Subscriptions). It detects three incident types within minutes (checkout failure spike, subscription renewal failures, refund wave), diagnoses a root cause from evidence, proposes catalog actions, and executes only what a deterministic policy proxy allows. Humans approve the rest in a dashboard. Everything is audited. Synthetic demo events are labeled.

## How we built it

Python 3.12, FastAPI, SQLAlchemy, a 30-second detector over playbook YAML, a four-node agent workflow (Triage → Diagnostician → Remediator → Verifier), a React + Vite + TypeScript dashboard with AG Grid Community (server-side rows, column groups, simulated badge), and a fictional demo shop (Lumen Coffee Co.).

## PayPal usage

- Sandbox REST: OAuth, Orders create/capture, subscription suspend/activate/capture, webhook signature verification.
- `@paypal/mcp` (official snake_case tools) as two scoped servers: read vs write.
- JS SDK v6 on the sandbox shop path.
- Webhooks + shop telemetry for detection. Transaction Search only for evidence.
- `PAYPAL_ENVIRONMENT` is `MOCK` or `SANDBOX`. Live mode cannot start.

## AI usage

- **Triage / Verifier:** `MODEL_FAST` (Azure OpenAI GPT via LiteLLM) — cheap classification and narrative.
- **Diagnostician / Remediator:** `MODEL_REASONING` (Azure GPT or Claude on Azure) — evidence-backed diagnosis and proposals.
- **`LLM_MODE=mock`:** deterministic playbook-aware stubs so CI and the judge clone run with no keys.
- Google ADK `LiteLlm` is the specified live wrapper; mock mode never imports it.

## Challenges

PayPal MCP tool names in early notes were dotted; the published package uses snake_case. Transaction Search lag rules out minute-level detection. Server-side capture without a buyer is not possible, so sandbox seed is synthetic+telemetry.

## Accomplishments

A working detect → diagnose → gate → execute → verify loop in mock mode, with the write boundary enforced by tests. The refund-wave path demonstrates a refused `refund.bulk`.

## What's next

Enable the webhook-gap playbook, live sandbox buyer flows, and hosted Render demo with the owner's keys.

## Built with

Python, FastAPI, SQLAlchemy, Alembic, Google ADK, LiteLLM, PayPal REST, `@paypal/mcp`, PayPal JS SDK v6, React, Vite, TypeScript, AG Grid Community, Docker, Render, PostgreSQL.
