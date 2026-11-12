# Decisions

Unspecified choices and any difference from the spec (`docs/spec.md`). Newest first.

## D-024 — The benchmark always runs on the mock gateway

`flatline/bench.py` scores seven scripted scenarios, two of them controls, plus
seven policy probes. It sets `PAYPAL_ENVIRONMENT=MOCK` itself, so a run can
never touch a PayPal account whatever `.env` says, and a live run costs model
calls only. With the stand in models the diagnosis column proves the plumbing,
not a model; the README and `docs/benchmark.md` say so next to the table. The
stand in gained a branch for PayPal server errors, which it used to report as
card declines.

## D-023 — Money limits in the proxy; no refund is automatic by default

Tiers say who decides; they did not say how much. The proxy now also enforces
`DAILY_REFUND_BUDGET` (the sum of refunds in the last 24 hours, read from the
money ledger and passed in, so the proxy stays free of I/O) and
`AUTO_REFUND_MAX`. The second one defaults to 0: the README and the video both
say that anything that moves money waits for a person, and that stays true
unless a merchant opts in. The executor checks the budget again before a
refund is sent, because several refunds can wait for approval at once, each
inside the budget on its own.

## D-022 — Recovery is planned by code, and the invoice writes are back

After an incident is resolved, `flatline/recovery/planner.py` lists the
customers whose checkout or renewal failed and files one proposal: PayPal
invoices for failed checkouts, a retry of the outstanding balance for failed
renewals. No model is involved. An invoice with an invented amount is the one
error this product cannot make, so the recovery actions are `planner_only` in
the catalog (the proxy refuses them from an agent) and the executor reads each
failed event again and bills the event's amount, not the proposal's.

D-019 removed the unused `create_invoice` and `send_invoice` writes. Recovery
uses them, so the write MCP session loads four tools again (`invoices.create`,
`invoices.send`, `invoices.sendReminder`, `payments.createRefund`). They follow
the D-016 rule: REST only when MCP provably sent nothing.

The incident stays `resolved` while a recovery proposal waits; approving it
does not run the verifier again. Payments are confirmed by
`INVOICING.INVOICE.PAID` and `PAYMENT.SALE.COMPLETED`. Sandbox buyers do not
pay invoices on their own, so the Chaos panel can inject those events for the
open requests; the ledger marks what they confirm as simulated. As in D-018,
customers that come from injected events are recorded as simulated in the
sandbox and nothing is sent for them.

Left out on purpose: refunding duplicate charges. It needs its own detector
and playbook, and it would be the first refund the agents initiate.

## D-021 — Each incident's agents see only that incident's evidence

Once the models stopped seeing the prepared answer, the live check showed the
real gap: the agents got the 50 most recent events of any kind, so a refund
wave and failed renewals were blamed on the previous checkout incident's
currency change. `tools.incident_events()` returns only the events matching
the incident's metric and scope inside its detection window (other traffic is
counted by type), and each playbook carries a short runbook of typical causes
and usual fixes. `live_check.py` now fails on a wrong cause or a missing fix.

## D-020 — The models reason from evidence, not from a prepared answer

Each live call used to include the playbook's deterministic answer with
"return this exact JSON shape, corrected from the input", so the model mostly
polished an answer it was handed, and the shop config it read still carried the
Chaos panel's `chaos` flags. Now the model gets the evidence and the JSON schema
of its answer only; the deterministic answer is the labelled fallback. The
agents' config history drops `chaos` and folds chaos-only versions, injected
events carry PayPal-shaped ids and no `synthetic` flag in the agents' view, and
config changes made from the Chaos panel get merchant-style notes (the test
intent is in the audit log as `chaos.inject`). The bulk refund is no longer in
the Remediator's draft: the refund playbook's `red_team_probe` makes the loop
add it, labelled as a probe, so the proxy's refusal is shown honestly.

## D-019 — The video is recorded by script, not by hand

`docs/DEMO_SCRIPT.md` (spec 15) described a manual click path. The clips are
recorded by a script (`demo-video/scripts/record-clips.mjs`, removed with the old cut) against the running stack,
so the file was removed. The renewal clip showed that the Remediator never
received the playbook's `allowed_actions` (the live model invented action
names); its input now carries them. Unused invoice create/send writes were
removed, so the write MCP session loads two tools.

## D-018 — Writes for injected incidents are simulated in the sandbox

The Chaos panel injects events with made up PayPal ids (`I-INJ-0`, `REF-INJ-0`).
Sending a reminder or a capture for those ids to the sandbox can only fail with
a 404. When every event behind an incident is synthetic and PayPal is not MOCK,
the executor records the PayPal write as `{"simulated": true}` and sends
nothing. Shop config actions, reads, OAuth and Transaction Search stay real.

## D-017 — One Render web service for the hosted demo

Render has no free background workers, so the Blueprint runs the detector and
the agent loop as daemon threads inside the API service (`RUN_WORKERS=true`).
Docker Compose keeps them as separate processes. Free services sleep after 15
minutes idle; the loops resume on the next request.

## D-016 — PayPal MCP wired for real; writes never retried blindly

`@paypal/mcp` 1.8.1 accepts dotted names in `--tools` (`orders.get`) and exposes
snake_case tool names over MCP (`get_order`). The old pool passed snake_case
names to `--tools`, so the server refused to start, and its call method was a
placeholder, so every read silently used REST. `mcp_pool.py` now opens an MCP
client session per scope over stdio. Reads still fall back to REST and record
`via: mcp|rest` in the Diagnostician's tool calls. A write falls back to REST
only on `McpUnavailable` or `McpRejected` (nothing reached PayPal); any other
error is raised so a refund can never be sent twice.

## D-015 — Models through LiteLLM only; Google ADK dropped

The nodes always called `litellm.completion` directly (D-007), so `google-adk`
was installed but never imported. It is removed from `requirements-live.txt`.
`MODEL_FAST` / `MODEL_REASONING` take any LiteLLM string: `gemini/...` (free tier
works), `ollama_chat/...` for a local model such as Qwen, or `azure/...`.

## D-014 — Repo cleanup before submission

The build brief for the coding agent (`AGENT_PROMPT.md`, `launch_cursor_agent.py`,
`PROGRESS.md`) and `spec.jpeg` were removed from the tree; `SPEC.md` and this log
moved into `docs/`. All of them remain in git history. The Remotion agent skills
under `demo-video/.agents/` are local tooling and are now git-ignored. Superseded
voiceover files were dropped; the video uses `public/audio/soundtrack-v2.m4a`.

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
- write: `create_refund`, `send_invoice_reminder` (the only two the executor
  uses; invoice creation was dropped so the write session holds less)

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
