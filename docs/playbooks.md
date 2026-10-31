# Playbooks

Thresholds live in `flatline/playbooks/*.yaml`.

## Checkout failure spike

**Detects.** Capture failures (shop `checkout.capture` with an error, plus `PAYMENT.CAPTURE.DENIED`) in a 5-minute window, at least 3× the 12-window baseline and at least 5 events.

**Typical fix.** If a config version shipped the wrong currency: auto banner + `shop.config.rollback` (approval). If many distinct buyers hit `INSTRUMENT_DECLINED`: alert + banner, no rollback.

## Subscription renewal failures

**Detects.** `BILLING.SUBSCRIPTION.PAYMENT.FAILED` clustered on one `plan_id` over 60 minutes.

**Typical fix.** `invoice.send_reminder` (auto) and `subscription.capture_outstanding` (approval). Optionally pause new sign-ups.

## Refund wave

**Detects.** `PAYMENT.CAPTURE.REFUNDED` far above baseline, or more than half of refunds in the window sharing one `product_id`.

**Typical fix.** Report + `shop.product.pause_sales` (approval). `refund.bulk` is catalogued as forbidden; if the agent proposes it, the proxy refuses and the incident is escalated with the written recommendation.

## Webhook gap (stretch, disabled)

**Detects.** Transactions with no matching webhook after a 3-hour reconcile lag.

**Typical fix.** Alert + `events.replay`. Not enabled in the default YAML (`enabled: false`).
