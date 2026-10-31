# Decisions

Unspecified choices and any difference from SPEC.md. Newest first.

## D-013 — Verification is re-checked; resolved incidents are not re-created

Found during the pre-video run on a clean Docker stack. `verify_incident`
ran exactly once, right after approval, when the injected failures were
still inside the verify window, so incidents stayed `verifying` forever.
The agents worker now re-checks every `verifying` incident every 15 s
(`reverify_pending`) and only writes a verifier step when the window is
quiet, to keep the timeline short. Second half: the detector's dedupe
excluded resolved incidents, so the same stale events would have spawned a
duplicate incident on the next 30 s scan. Dedupe now matches the latest
incident for the scope regardless of status and reopens a resolved one
(queuing agents again) only if `min_count` matching events arrived after
`resolved_at`. Covered by `test_detector.py`.

## D-012 — Product name is Flatline

The owner asked for the project to be called **Flatline** (matching the
GitHub remote), then asked for the old name to be removed everywhere. The
Python package was renamed `warden/` → `flatline/` (all imports, loggers,
Dockerfile, Compose/Render commands, CI, Makefile, alembic), the shop env var
became `FLATLINE_API_URL`, the Postgres user/password/db became `flatline`
(existing volumes must be recreated: `docker compose down -v && make up`),
and dashboard storage keys/events were renamed. `SPEC.md`,
`AGENT_PROMPT.md` and `launch_cursor_agent.py` are the original brief and
were left as written; "original Flatline" in D-002 refers to the earlier
Kubernetes project this design was reused from.

## D-011 — This repo is the payments product only

The working tree used to be the original Kubernetes SRE project with
payments nested in a subfolder. That previous
product is gone from this folder. The PayPal hackathon app is now the
repository root so `cp .env.example .env && make up` matches SPEC.md.

## D-010 — Compose does not publish Postgres; chaos injects + scans immediately

Host 5432 is often already taken by a local Postgres. The compose Postgres
stays on the Docker network only. The API has a `/healthz` check; seed,
shop, detector, and agents wait until it is healthy. `scripts/seed.py`
retries for ~30s. Chaos buttons write synthetic events and run `scan_once`
in the same request so the judge does not wait 30s for the detector loop.

Docker Compose `env_file` treats `KEY=value  # comment` as part of the
value. `.env.example` now keeps comments on their own lines. Notify
ignores anything that is not `http(s)://`.

## D-000 — Payments app is the repository root

SPEC.md originally said to nest the build in a subfolder if this folder
already held the Kubernetes SRE project. The owner later asked to drop that
previous product and keep only the PayPal hackathon work. Layout is now the
SPEC.md Section 6 tree at the repo root.

## D-001 — AGENT_PROMPT.md was missing

Only `SPEC.md`, `spec.jpeg`, and `launch_cursor_agent.py` were present at
the start. `AGENT_PROMPT.md` was written from the owner's launch
instructions.

## D-002 — Reuse from original Flatline

Read-only reuse of ideas and patterns, not files copied wholesale:

- Safety model: agents never hold write credentials; a deterministic policy
  layer (plain code) is the gate.
- Four-node pipeline: Triage → Diagnostician → Remediator → Verifier, with
  orchestration as sequential Python rather than an ADK multi-agent tree
  (same reason as original Flatline: inspectable handoffs).
- `pydantic-settings` config object, ruff + pytest layout, MIT license
  wording.
- Dashboard visual language (Archivo / IBM Plex, gold accent, light/dark,
  large type for video).
- Secret-scan CI step and `.env*` gitignore rules.

## D-009 — Live extras are optional installs

`google-adk`, `litellm` and `mcp` live in `requirements-live.txt` so `make up`
and CI do not depend on them. Mock mode never imports them. Live LLM still
uses LiteLLM as specified.

## D-008 — SANDBOX seed cannot capture without a buyer

PayPal Checkout capture requires buyer approval. `scripts/seed.py` in SANDBOX
posts synthetic events + shop telemetry and does not create real captured
orders. Recorded so we do not claim otherwise.

## D-007 — Sequential Python workflow, ADK on the live path only

Same choice as original Flatline: four nodes run in plain async Python so
handoffs are inspectable. `LLM_MODE=mock` never imports `google-adk` or
`litellm`. `LLM_MODE=live` calls LiteLLM (`google.adk.models.lite_llm.LiteLlm`
is available; we call `litellm.completion` directly to keep node I/O as
pydantic models). LiteLLM is pinned `>=1.84,!=1.82.7,!=1.82.8` after the
March 2026 supply-chain incident.

## D-006 — PayPal JS SDK v6 for the sandbox shop

The demo shop uses `https://www.paypal.com/web-sdk/v6/core` with
`createInstance({ clientId })` and `createPayPalOneTimePaymentSession`.
MOCK mode uses a "Pay (mock)" button and never loads the SDK.

## D-005 — Sync SQLAlchemy, SQLite in tests

SPEC allows SQLite only for unit tests. Integration and in-process e2e also
use file-backed SQLite so CI needs no Postgres. Docker Compose and Render
use PostgreSQL 16. The API uses sync SQLAlchemy sessions (not asyncio) —
simpler, and FastAPI runs them in a threadpool.

## D-004 — PayPal MCP tool names are snake_case

SPEC.md §9.4 listed dotted identifiers (`transactions.list`, `orders.get`,
`payments.createRefund`, …). The official `@paypal/mcp` README (v1.8.1,
https://www.npmjs.com/package/@paypal/mcp) uses snake_case:

- read: `list_transactions`, `get_order`, `get_refund`,
  `show_subscription_details`, `show_subscription_plan_details`,
  `list_subscription_plans`, `list_disputes`, `get_dispute`,
  `list_invoices`, `get_invoice`
- write: `create_refund`, `create_invoice`, `send_invoice`,
  `send_invoice_reminder`

`mcp_pool.py` uses the official names. Subscription suspend / activate /
capture are not MCP tools; SandboxGateway calls the sandbox REST endpoints.

`get_merchant_insights` is not in `@paypal/mcp` 1.8.1. Mock returns a stub;
sandbox returns `{available: false}`.

MCP stdio JSON-RPC is spawned for the judge/sandbox path; REST is the
tested fallback so MOCK tests never depend on `npx`.

## D-003 — No live PayPal host string

`Settings.paypal_api_base` returns the sandbox host only when
`PAYPAL_ENVIRONMENT=SANDBOX`, otherwise empty. There is no
`api-m.paypal.com` (live) constant anywhere.
