# Flatline: Devpost submission text

Paste each section into the matching Devpost field. Fill the three links under "Try it" once they exist.

## Inspiration

Every online shop monitors its servers. Almost nobody monitors their money. When checkout breaks on a Friday evening, or refunds suddenly pile up on one product, a small merchant usually finds out days later from a payout report or an annoyed customer.

Earlier this year I built Warden, an SRE agent for Kubernetes with one hard rule: the agents diagnose and propose, but they never hold write credentials. Payments have the same shape of problem, and the same rule matters even more when the action is a refund. Flatline is that idea, rebuilt for a merchant's PayPal revenue.

## What it does

Flatline is on call for a merchant's PayPal integration. It watches checkout, refunds and subscription renewals through PayPal webhooks and the shop's own checkout telemetry. Every 30 seconds a detector compares a five minute window with a rolling baseline. When a metric breaks its baseline, an incident opens and four agents work it in order:

1. **Triage** sets the severity, the scope and the money at risk per hour.
2. **Diagnostician** reads PayPal through the read scoped PayPal MCP server, plus the event store and config history, and names the root cause with evidence: event ids, order ids, config versions.
3. **Remediator** proposes fixes, chosen only from a fixed catalog of actions.
4. **Verifier** waits for a quiet window and confirms recovery against the metric.

Every proposal then goes through a policy proxy written in plain Python, not a prompt. Small reversible fixes, like a warning banner on the shop or a payment reminder, run on their own. Anything that moves money or changes config waits for a human in the dashboard. Anything outside the catalog is refused, such as the bulk refund the agent tries in the demo. Only the executor behind the proxy can write to PayPal, and every detection, step, decision, approval and execution lands in an audit log.

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

1. Each agent calls a model through LiteLLM. Triage and Verifier use a fast model, Diagnostician and Remediator a stronger one. The demo uses Google Gemini on the free tier (Gemini 2.5 Flash for Triage and Verifier, Gemini 2.5 Pro for Diagnostician and Remediator); the same build runs fully on premises with Qwen through Ollama, or on Azure OpenAI, by changing two settings.
2. Each agent receives the real incident data (events, config history, PayPal reads) and a deterministic playbook answer that fixes the JSON shape and serves as the fallback.
3. If a model call fails, for example on a rate limit, the agent keeps the playbook answer and the timeline labels that step as a fallback. A step is never credited to a model that did not produce it.
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
3. The refund scenario shows the safety model on screen: the agent asks for a bulk refund, and the proxy refuses it.
4. More than 80 automated tests run in CI with no keys.

## What I learned

An agent that touches money is mostly a permissions problem, not a prompting problem. Once the write path was small, explicit and audited, giving the model real freedom in diagnosis became easy to justify.

## What's next

1. Turn on the webhook gap playbook, which reconciles transactions against webhooks after the Transaction Search lag.
2. Approval notifications to Slack or email.
3. More playbooks, such as dispute spikes and payout holds.

## Try it

1. Demo video: YOUTUBE_LINK
2. Code: https://github.com/mazzyy/Flatline
3. Hosted demo: RENDER_LINK (dashboard passcode in the testing instructions)
4. Run locally with no keys: `cp .env.example .env && make up`, open http://localhost:8000 (passcode `demo-judge`) and use the Chaos panel.

## Testing instructions for judges

Sign in to the hosted dashboard with passcode DASHBOARD_PASSCODE and inject token INJECT_TOKEN (the token unlocks the Chaos panel). In Chaos, click **Ship bad currency config** to start the checkout scenario; the detector opens an incident within about 30 seconds. Open it to see the root cause, the agent timeline (with the model behind each step and whether PayPal was read through MCP) and the proposals, then approve the rollback. **Inject refund wave** shows the refused bulk refund, and **Inject subscription renewal failures** shows an automatic reminder next to a capture that waits for approval. **Reset all chaos** puts everything back. The hosted demo runs on free Render instances, so the first page load can take about a minute. Everything runs against the PayPal sandbox; no real money moves.

## Built with

python, fastapi, sqlalchemy, postgresql, alembic, litellm, gemini, ollama, qwen, paypal, paypal-mcp, paypal-js-sdk, model-context-protocol, react, vite, typescript, ag-grid, node.js, docker, render, remotion
