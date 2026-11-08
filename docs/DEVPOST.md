# Flatline: Devpost submission text

Paste each section into the matching Devpost field. Replace YOUTUBE_LINK once the video is uploaded.

## Inspiration

Every online shop monitors its servers. Almost nobody monitors their money. When checkout breaks on a Friday evening, or refunds suddenly pile up on one product, a small merchant usually finds out days later from a payout report or an annoyed customer.

Earlier this year I built Warden, an SRE agent for Kubernetes with one hard rule: the agents diagnose and propose, but they never hold write credentials. Payments have the same shape of problem, and the same rule matters even more when the action is a refund. Flatline is that idea, rebuilt for a merchant's PayPal revenue.

## What it does

Flatline is on call for a merchant's PayPal integration. It watches checkout, refunds and subscription renewals through PayPal webhooks and the shop's own checkout telemetry. Every 30 seconds a detector compares a five minute window with a rolling baseline. When a metric breaks its baseline, an incident opens and four agents work it in order:

1. **Triage** sets the severity, the scope and the money at risk per hour.
2. **Diagnostician** reads PayPal through the read scoped PayPal MCP server, plus the event store and config history, and names the root cause with evidence: event ids, order ids, config versions.
3. **Remediator** proposes fixes, chosen only from a fixed catalog of actions.
4. **Verifier** waits for a quiet window and confirms recovery against the metric.

Every proposal then goes through a policy proxy written in plain Python, not a prompt. Small reversible fixes, like a warning banner on the shop or a payment reminder, run on their own. Anything that moves money or changes config waits for a human in the dashboard. Anything outside the catalog is refused, such as the bulk refund I slip in as a red-team probe in the demo. Only the executor behind the proxy can write to PayPal, and every detection, step, decision, approval and execution lands in an audit log.

The demo runs three playbooks: a checkout failure spike caused by a bad currency config, a refund wave concentrated on one product, and failed subscription renewals on one plan.

## What I built during the hackathon

Flatline is a new codebase started in the submission period. From Warden it takes two design ideas: agents without write credentials, and a policy proxy in code. Everything payments specific is new: the PayPal sandbox gateway, webhook verification, the two scoped PayPal MCP sessions, the detector and playbooks, the agents and their prompts, the policy catalog and executor, the dashboard, the demo shop, the sandbox setup script, the tests and the demo video.

## How I built it

The backend is Python 3.12 with FastAPI for ingest, webhooks, the dashboard API and live updates over server sent events, SQLAlchemy 2 with PostgreSQL 16 for storage, and Alembic for migrations. The detector reads its thresholds from playbook YAML files. The four agents call models through LiteLLM. The dashboard is React, Vite and TypeScript, with AG Grid Community for the transactions grid (server side rows, column groups, a simulated badge for injected events). The demo shop, Lumen Coffee Co., is a small Node server with the PayPal JS SDK v6. Everything runs with Docker Compose locally and deploys to Render from a Blueprint. The demo video is made in code with Remotion, with an original soundtrack.

## How it uses PayPal

1. **Sandbox REST APIs:** OAuth client credentials, Orders create and capture in the shop, captured payment refunds, Subscriptions (show, suspend, activate, capture outstanding balance), Invoicing reminders, Catalog Products and Billing Plans (the setup script creates the Coffee Club plan), and Transaction Search and plan details as evidence for the Diagnostician.
2. **The official PayPal MCP server (`@paypal/mcp` 1.8.1), run as two separate sessions.** The read session only loads read tools and serves the agents. The write session only loads write tools and is used by the executor alone, so least privilege is enforced by the MCP server itself, not just by our code. Each agent step records whether a PayPal read went through MCP or fell back to REST.
3. **Webhooks** with signature verification through `verify-webhook-signature`. Detection runs on webhooks and shop telemetry, because Transaction Search can lag by up to three hours.
4. **JS SDK v6** buttons on the demo shop.
5. **Sandbox only.** `PAYPAL_ENVIRONMENT` must be `MOCK` or `SANDBOX`; any other value refuses to start, and there is no live host string in the code.
6. **Honest about injected data.** The Chaos panel injects events with made up PayPal ids. For those incidents the executor records PayPal writes as simulated instead of sending a request that can only fail; shop config changes, reads, OAuth and Transaction Search are real sandbox calls.

## How it uses AI

1. Each agent calls a model through LiteLLM. Triage and Verifier use a fast model, Diagnostician and Remediator a stronger one. The demo uses Google Gemini on the free tier (Gemini 2.5 Flash Lite for Triage and Verifier, Gemini 2.5 Flash for Diagnostician and Remediator, with other Gemini models as fallbacks when one is rate limited); the same build runs fully on premises with Qwen through Ollama, or on Azure OpenAI, by changing two settings.
2. Each agent receives the real incident data (events, config history, PayPal reads through MCP) and the JSON schema of its answer, never a prepared answer. The Diagnostician must back every claim with evidence (an event id, config version or PayPal id), and the Remediator can only choose from the playbook's allowed actions. The agents are not told which events were injected, so they have to find the cause in the data.
3. If a model call fails, for example on a rate limit, the next model in `MODEL_FALLBACKS` is tried; if all fail, the agent keeps the playbook's deterministic answer and the timeline labels that step as a fallback. A step is always credited to the model that actually answered.
4. The model never acts alone. Its proposals pass the policy proxy, and the Verifier's resolved flag comes from the metric check; the model only writes the explanation.
5. `LLM_MODE=mock` runs the identical flow with deterministic stand ins, so anyone can run the project with no keys.

## Challenges I ran into

1. Transaction Search lags by up to three hours, so it cannot be the detection clock. Detection had to run on webhooks and shop telemetry, with Transaction Search used only as evidence.
2. The PayPal MCP server takes dotted tool names on the command line (`orders.get`) but exposes snake_case names over MCP (`get_order`). Getting that wrong means the server refuses to start, which our first version did silently.
3. Retrying writes safely. A refund sent through MCP must never be retried over REST unless it provably never reached PayPal, so the client tells "server down" and "arguments rejected" apart from everything else.
4. Keeping the AI honest. An early version quietly fell back to canned answers when a model call failed. Now every fallback is visible in the dashboard.

## Accomplishments that I'm proud of

1. The whole loop runs end to end against the PayPal sandbox: detect, diagnose, gate, execute, verify.
2. The write boundary is enforced three ways: agents get a read only gateway whose write methods raise, an import boundary test keeps agent code away from the writer, and the PayPal MCP read session does not even load write tools.
3. The refund scenario shows the safety model on screen: a red-team probe slips a forbidden bulk refund in next to the agent's proposals, and the proxy refuses it.
4. More than 80 automated tests run in CI with no keys.

## What I learned

An agent that touches money is mostly a permissions problem, not a prompting problem. Once the write path was small, explicit and audited, giving the model real freedom in diagnosis became easy to justify.

## What's next

1. Turn on the webhook gap playbook, which reconciles transactions against webhooks after the Transaction Search lag.
2. Approval notifications to Slack or email.
3. More playbooks, such as dispute spikes and payout holds.

## Try it

1. Demo video: YOUTUBE_LINK
2. Code: https://github.com/mazzyy/Flatline (MIT)
3. Run it yourself: the README has complete setup and run instructions. With Docker installed it is `git clone https://github.com/mazzyy/Flatline && cd Flatline && cp .env.example .env && make up`, no keys needed.

## Testing instructions for judges

1. Clone the repo and run `cp .env.example .env && make up` (Docker required). This starts the API, dashboard, detector, agent loop, Postgres and the demo shop in mock mode, so no PayPal or model keys are needed.
2. Open http://localhost:8000 and log in with passcode `demo-judge` and inject token `change-me` (the token unlocks the Chaos panel). The demo shop is at http://localhost:3000.
3. In Chaos, click **Ship bad currency config**. The detector opens an incident within about 30 seconds. Open it to see the root cause, the agent timeline and the proposals, then approve the rollback.
4. **Inject refund wave** shows the refused bulk refund. **Inject subscription renewal failures** shows the Diagnostician reading the plan from PayPal and an automatic payment reminder; if the model also proposes capturing the balance, that waits for approval. **Reset all chaos** puts everything back.
5. To run it against the PayPal sandbox with live models, follow "Connect the PayPal sandbox" in the README (a sandbox REST app and a free Gemini API key, or a local Qwen through Ollama), then run `python scripts/live_check.py`. It plays all three scenarios and prints each agent step with its model, latency and whether PayPal was read through the MCP server. This is how the demo video was recorded. No real money moves anywhere.

## Built with

python, fastapi, sqlalchemy, postgresql, alembic, litellm, gemini, ollama, qwen, paypal, paypal-mcp, paypal-js-sdk, model-context-protocol, react, vite, typescript, ag-grid, node.js, docker, render, remotion
