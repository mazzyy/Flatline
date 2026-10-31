# Agent prompt — Warden for Payments

You are building **Warden for Payments** for the PayPal AI Hackathon (deadline
Nov 12, 2026, 12:00 PST). Work fully autonomously.

## Source of truth

1. Read `SPEC.md` and this file completely before writing any code. `SPEC.md`
   wins if they conflict.
2. If this folder already contains other code (for example the original Warden
   project), do not modify it. Create the new project in `warden-pay/`, copy
   `SPEC.md` and this file into it, and build everything there. You may read
   the existing Warden code and reuse ideas; record reuse in `DECISIONS.md`.

## How you work

3. Build milestone by milestone, M0 to M10 from SPEC.md Section 14, in order.
   For each milestone: implement it fully, run lint and all tests, fix until
   green, update `PROGRESS.md`, and make a git commit `M<n>: <summary>`. Then
   continue immediately with the next milestone.
4. Do not ask questions and do not stop to wait for confirmation. When
   something is unclear, choose the simplest option consistent with SPEC.md,
   write it in `DECISIONS.md`, and keep going.
5. Everything must build, run and pass tests with `PAYPAL_ENVIRONMENT=MOCK`
   and `LLM_MODE=mock` and no secrets. Implement the real PayPal sandbox and
   live LLM paths too, but never make tests depend on them. Never add any
   code path to live PayPal. Never commit secrets.
6. Keep the safety model exactly as specified: agents only get read-only
   PayPal access; only the executor writes, and only after the deterministic
   policy proxy allows it.
7. Before relying on any PayPal MCP tool name, PayPal REST endpoint, or
   Google ADK / LiteLLM API, check the official docs or package README, and
   record any difference from SPEC.md in `DECISIONS.md`.
8. Do not claim features in README or docs that do not work.

## When you stop

Only stop when all milestones M0–M10 are done, `make demo-test` passes, and
`cp .env.example .env && make up` starts the full stack in mock mode. Then
give one final report: milestones completed, test results, key decisions, and
the manual steps the owner needs to do (PayPal sandbox app and webhook,
subscription plan, Azure keys, Render deploy).

End your last message of a run with exactly one of:

```
STATUS: COMPLETE — M0–M10 done, demo-test green
STATUS: CONTINUE — next unfinished milestone is M<n>
STATUS: BLOCKED — <one-line reason that a human must resolve>
```
