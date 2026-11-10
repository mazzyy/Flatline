# Playbooks

Thresholds live in `flatline/playbooks/*.yaml`.

## Checkout failure spike

**Detects.** Capture failures (shop `checkout.capture` with an error, plus `PAYMENT.CAPTURE.DENIED`) in a 5-minute window, at least 3× the 12-window baseline and at least 5 events.

**Typical fix.** If a config version shipped the wrong currency: auto banner + `shop.config.rollback` (approval). If many distinct buyers hit `INSTRUMENT_DECLINED`: alert + banner, no rollback.

**Recovery.** Once resolved: `recovery.payment_links.send` (approval), one PayPal invoice per customer whose capture failed. Declined cards (`skip_error_codes` in the YAML), customers who have paid since and events without an amount are left alone.

## Subscription renewal failures

**Detects.** `BILLING.SUBSCRIPTION.PAYMENT.FAILED` clustered on one `plan_id` over 60 minutes.

**Typical fix.** `invoice.send_reminder` (auto) and `subscription.capture_outstanding` (approval). Optionally pause new sign-ups.

**Recovery.** Once resolved: `recovery.renewals.retry` (approval), one retry of the outstanding balance per subscriber who has not paid since.

## Refund wave

**Detects.** `PAYMENT.CAPTURE.REFUNDED` far above baseline, or more than half of refunds in the window sharing one `product_id`.

**Typical fix.** Report + `shop.product.pause_sales` (approval). `refund.bulk` is catalogued as forbidden; if the agent proposes it, the proxy refuses and the incident is escalated with the written recommendation.

**Recovery.** None: the money has gone back to the buyers. The ledger records the refunded total as the incident's impact.

## Webhook gap (stretch, disabled)

**Detects.** Transactions with no matching webhook after a 3-hour reconcile lag.

**Typical fix.** Alert + `events.replay`. Not enabled in the default YAML (`enabled: false`).

## Recovery

A playbook's `recovery` block names the action the planner files after the incident is resolved. The planner (`flatline/recovery/planner.py`) is plain code: it reads the failed events since the detection window opened, counts one lost sale per buyer, order or subscription, and lists the ones worth asking back. Recovery actions are marked `planner_only` in the catalog, so the proxy refuses them from an agent, and both are capped by `RECOVERY_MAX_LINKS` and `RECOVERY_MAX_TOTAL`.
