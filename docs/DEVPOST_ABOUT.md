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

Then it finishes the job. Once the verifier has resolved an incident, a recovery planner reads the failed events and lists the customers who tried to pay and could not. One approval sends each of them a PayPal invoice for the order they tried to place, or retries each failed renewal. When PayPal reports a payment, a ledger moves that amount from asked back to recovered, and the dashboard shows lost, asked back and recovered side by side. The planner is plain code with no model in it, so no amount or customer can be invented.

Money has limits in code as well as tiers: a cap per refund, a daily refund budget that is checked again at the moment of sending, and caps on how much one recovery may ask back. No refund runs on its own unless the merchant opts in.

The demo runs three playbooks: a checkout failure spike caused by a bad currency config, a refund wave concentrated on one product, and failed subscription renewals on one plan. The video shows the first one from failure to recovered money, including a real sandbox invoice being sent and paid.

## How we built it

The backend is Python 3.12 with FastAPI for ingest, webhooks, the dashboard API and live updates over server sent events, SQLAlchemy 2 with PostgreSQL 16 for storage, and Alembic for migrations. The detector reads its thresholds from playbook YAML files. The four agents call models through LiteLLM. The dashboard is React, Vite and TypeScript, with AG Grid Community for the transactions grid (server side rows, column groups, a simulated badge for injected events). The demo shop, Lumen Coffee Co., is a small Node server with the PayPal JS SDK v6. Everything runs with Docker Compose locally, and the live demo is one container on Heroku that serves the dashboard and the shop behind one address. The demo video is made in code with Remotion, with an original soundtrack.

Flatline is a new codebase started in the submission period. From Warden it takes two design ideas: agents without write credentials, and a policy proxy in code. Everything payments specific is new: the PayPal sandbox gateway, webhook verification, the two scoped PayPal MCP sessions, the detector and playbooks, the agents and their prompts, the policy catalog and executor, the recovery planner and money ledger, the benchmark, the dashboard, the demo shop, the sandbox setup script, the tests and the demo video.

### How it uses PayPal

1. **Sandbox REST APIs:** OAuth client credentials, Orders create and capture in the shop, captured payment refunds, Subscriptions (show, suspend, activate, capture outstanding balance), Invoicing (reminders, and create and send for recovery), Catalog Products and Billing Plans (the setup script creates the Coffee Club plan), and Transaction Search and plan details as evidence for the Diagnostician.
2. **The official PayPal MCP server (`@paypal/mcp` 1.8.1), run as two separate sessions.** The read session only loads read tools and serves the agents. The write session only loads write tools (refund, invoice create, invoice send, invoice reminder) and is used by the executor alone, so least privilege is enforced by the MCP server itself, not just by our code. Each agent step records whether a PayPal read went through MCP or fell back to REST.
3. **Webhooks** with signature verification through `verify-webhook-signature`. Detection runs on webhooks and shop telemetry, because Transaction Search can lag by up to three hours. `INVOICING.INVOICE.PAID` and `PAYMENT.SALE.COMPLETED` confirm a recovery.
4. **JS SDK v6** buttons on the demo shop.
5. **Sandbox only.** `PAYPAL_ENVIRONMENT` must be `MOCK` or `SANDBOX`; any other value refuses to start, and there is no live host string in the code.
6. **Honest about injected data.** The Chaos panel injects events with made up PayPal ids. For those incidents the executor records PayPal writes as simulated instead of sending a request that can only fail; shop config changes, reads, OAuth and Transaction Search are real sandbox calls. Recovery follows the same rule per customer, and because sandbox buyers do not pay invoices on their own, a Chaos button plays the paying customers and the ledger marks those payments as simulated.

### How it uses AI

1. Each agent calls a model through LiteLLM. Triage and Verifier use a fast model, Diagnostician and Remediator a stronger one. The demo uses Google Gemini on the free tier (Gemini 2.5 Flash Lite for Triage and Verifier, Gemini 2.5 Flash for Diagnostician and Remediator, with other Gemini models and a local Qwen 2.5 7B through Ollama as fallbacks when one is rate limited). Each step in the dashboard names the model that answered it. In the video every step was answered by Gemini. The same build runs fully on premises with Qwen, or on Azure OpenAI, by changing two settings.
2. Each agent receives the real incident data (events, config history, PayPal reads through MCP) and the JSON schema of its answer, never a prepared answer. The Diagnostician must back every claim with evidence (an event id, config version or PayPal id), and the Remediator can only choose from the playbook's allowed actions. The agents are not told which events were injected, so they have to find the cause in the data.
3. If a model call fails, for example on a rate limit, the next model in `MODEL_FALLBACKS` is tried; if all fail, the agent keeps the playbook's deterministic answer and the timeline labels that step as a fallback. A step is always credited to the model that actually answered.
4. The model never acts alone. Its proposals pass the policy proxy, and the Verifier's resolved flag comes from the metric check; the model only writes the explanation.
5. `LLM_MODE=mock` runs the identical flow with deterministic stand ins, so anyone can run the project with no keys.
6. Where the AI is left out on purpose: recovery. Who is asked to pay, and how much, comes from code over the event store. The proxy refuses a recovery action that an agent proposes.

## Challenges we ran into

1. Transaction Search lags by up to three hours, so it cannot be the detection clock. Detection had to run on webhooks and shop telemetry, with Transaction Search used only as evidence.
2. The PayPal MCP server takes dotted tool names on the command line (`orders.get`) but exposes snake_case names over MCP (`get_order`). Getting that wrong means the server refuses to start, which our first version did silently.
3. Retrying writes safely. A refund sent through MCP must never be retried over REST unless it provably never reached PayPal, so the client tells "server down" and "arguments rejected" apart from everything else.
4. Keeping the AI honest. An early version quietly fell back to canned answers when a model call failed. Now every fallback is visible in the dashboard.

## Accomplishments that we're proud of

1. The whole loop runs end to end against the PayPal sandbox: detect, diagnose, gate, execute, verify.
2. The write boundary is enforced three ways: agents get a read only gateway whose write methods raise, an import boundary test keeps agent code away from the writer, and the PayPal MCP read session does not even load write tools.
3. The refund scenario shows the safety model on screen: a red-team probe slips a forbidden bulk refund in next to the agent's proposals, and the proxy refuses it.
4. 130 automated tests run with no keys.
5. It does not stop at "resolved". In the checkout scenario six customers lost a $108 sale between them; one approval sends six invoices, and the ledger shows what came back.
6. A benchmark (`make bench`) scores seven scripted scenarios on detection, diagnosis, gating, safety and recovery, with two quiet day controls and seven policy probes. 34 of 34 checks pass with the stand in models, and `make bench-live` scores real models on the same scenarios.

## What we learned

An agent that touches money is mostly a permissions problem, not a prompting problem. Once the write path was small, explicit and audited, giving the model real freedom in diagnosis became easy to justify.

## What's next for Flatline

1. Turn on the webhook gap playbook, which reconciles transactions against webhooks after the Transaction Search lag.
2. Approval notifications to Slack or email.
3. More playbooks, such as dispute spikes and payout holds.
4. Duplicate charges: detect them and propose the refund, inside the per refund limit and the daily budget.

## Try it

1. Live demo: https://flatline-demo-27612c3a852c.herokuapp.com (passcode `demo-judge`), demo shop at https://flatline-demo-27612c3a852c.herokuapp.com/shop
2. Demo video: https://youtu.be/z9Kkz_AERaY
3. Code: https://github.com/mazzyy/Flatline (MIT)
4. Run it yourself: the README has complete setup and run instructions. With Docker installed it is `git clone https://github.com/mazzyy/Flatline && cd Flatline && cp .env.example .env && make up`, no keys needed.

## Testing instructions for judges

The quick way, nothing to install:

1. Open the demo shop at https://flatline-demo-27612c3a852c.herokuapp.com/shop, pick a coffee and press **Pay without a PayPal login (demo)**. The payment goes through.
2. Open https://flatline-demo-27612c3a852c.herokuapp.com, log in with passcode `demo-judge`, and look at **Transactions**: your payment is at the top.
3. Open **Chaos** and click **Ship bad currency config**. An incident opens within seconds. Open it to see the root cause, the agent timeline and the proposals, then approve the rollback.
4. Wait about a minute. A recovery proposal appears on the same incident with the six customers and $108. Approve it, press **Customers pay their recovery requests** in Chaos, and the Overview shows what was recovered.
5. **Inject refund wave** shows the refused bulk refund. **Inject subscription renewal failures** shows the Diagnostician reading the plan from PayPal and an automatic payment reminder. **Reset all chaos** puts everything back.

The live demo runs on the PayPal sandbox with live models. No real money moves anywhere.

To run it yourself:

1. Clone the repo and run `cp .env.example .env && make up` (Docker required). This starts everything in mock mode, so no PayPal or model keys are needed. The dashboard is at http://localhost:8000 (passcode `demo-judge`, inject token `change-me`) and the shop at http://localhost:3000.
2. `make bench` runs the scored benchmark in a few seconds, with no keys (needs the Python setup from the README).
3. To run it against the PayPal sandbox with live models, follow "Connect the PayPal sandbox" in the README, then run `python scripts/live_check.py`.
