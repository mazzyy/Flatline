"""Action catalog. Anything not listed is forbidden."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Tier = Literal["auto", "approval", "forbidden"]


@dataclass(frozen=True)
class ActionSpec:
    key: str
    tier: Tier
    description: str
    notes: str = ""
    params: str = ""  # what the executor reads, shown to the Remediator
    # Planned by code from the event store. The proxy refuses it from an agent.
    planner_only: bool = False


ACTIONS: dict[str, ActionSpec] = {
    "notify.alert": ActionSpec(
        "notify.alert",
        "auto",
        "Log an alert and optionally POST NOTIFY_WEBHOOK_URL",
        params='{"message": str}',
    ),
    "report.create": ActionSpec(
        "report.create",
        "auto",
        "Attach a markdown report to the incident",
        params='{"markdown": str}',
    ),
    "shop.banner.set": ActionSpec(
        "shop.banner.set", "auto", "Set the shop-wide banner", params='{"text": str}'
    ),
    "shop.banner.clear": ActionSpec("shop.banner.clear", "auto", "Clear the shop-wide banner"),
    "invoice.send_reminder": ActionSpec(
        "invoice.send_reminder",
        "auto",
        "Send a reminder to one subscriber",
        params='{"invoice_id": str, "subscription_id": str}',
    ),
    "shop.config.rollback": ActionSpec(
        "shop.config.rollback",
        "approval",
        "Activate a previous shop config version",
        params='{"version": int, the last good version}',
    ),
    "shop.product.pause_sales": ActionSpec(
        "shop.product.pause_sales",
        "approval",
        "Pause sales of one product",
        params='{"product_id": str}',
    ),
    "shop.product.resume_sales": ActionSpec(
        "shop.product.resume_sales",
        "approval",
        "Resume sales of one product",
        params='{"product_id": str}',
    ),
    "shop.plan.pause_signups": ActionSpec(
        "shop.plan.pause_signups",
        "approval",
        "Pause new sign-ups on a plan",
        params='{"plan_id": str}',
    ),
    "shop.plan.resume_signups": ActionSpec(
        "shop.plan.resume_signups", "approval", "Resume plan sign-ups", params='{"plan_id": str}'
    ),
    "subscription.capture_outstanding": ActionSpec(
        "subscription.capture_outstanding",
        "approval",
        "Capture outstanding balance via REST",
        params='{"subscription_id": str}',
    ),
    "subscription.suspend": ActionSpec(
        "subscription.suspend",
        "approval",
        "Suspend one subscription",
        params='{"subscription_id": str, "reason": str}',
    ),
    "subscription.activate": ActionSpec(
        "subscription.activate",
        "approval",
        "Activate one subscription",
        params='{"subscription_id": str, "reason": str}',
    ),
    "refund.single": ActionSpec(
        "refund.single",
        "approval",
        "Refund one capture if amount ≤ REFUND_APPROVAL_MAX",
        notes="Runs on its own only at or under AUTO_REFUND_MAX (off by default). "
        "Counts against DAILY_REFUND_BUDGET.",
        params='{"capture_id": str, "amount": str, "currency": str}',
    ),
    "recovery.payment_links.send": ActionSpec(
        "recovery.payment_links.send",
        "approval",
        "Send a PayPal invoice to each customer whose checkout failed during the incident",
        notes="Planned by code after the incident is resolved, never by a model. "
        "Capped by RECOVERY_MAX_LINKS and RECOVERY_MAX_TOTAL.",
        params='{"items": [{"event_id": str, "order_id": str, "amount": str}]}',
        planner_only=True,
    ),
    "recovery.renewals.retry": ActionSpec(
        "recovery.renewals.retry",
        "approval",
        "Retry the outstanding balance of each subscriber whose renewal failed",
        notes="Planned by code after the incident is resolved, never by a model. "
        "Capped by RECOVERY_MAX_LINKS and RECOVERY_MAX_TOTAL.",
        params='{"items": [{"event_id": str, "subscription_id": str, "amount": str}]}',
        planner_only=True,
    ),
    "events.replay": ActionSpec(
        "events.replay", "approval", "Replay missing webhook events", params='{"event_ids": [str]}'
    ),
    "refund.bulk": ActionSpec("refund.bulk", "forbidden", "Bulk refunds are never agent-initiated"),
    "subscription.cancel": ActionSpec("subscription.cancel", "forbidden", "Cancel is human-only"),
    "subscription.cancel_at_period_end": ActionSpec(
        "subscription.cancel_at_period_end", "forbidden", "Cancel is human-only"
    ),
    "dispute.accept": ActionSpec("dispute.accept", "forbidden", "Accepting a claim is human-only"),
    "dispute.accept_claim": ActionSpec(
        "dispute.accept_claim", "forbidden", "Accepting a claim is human-only"
    ),
    "payout.create": ActionSpec("payout.create", "forbidden", "Payouts are out of scope"),
    "credentials.rotate": ActionSpec(
        "credentials.rotate", "forbidden", "Credential changes are human-only"
    ),
    "webhook.delete": ActionSpec("webhook.delete", "forbidden", "Webhook deletion is human-only"),
}


def get(key: str) -> ActionSpec | None:
    return ACTIONS.get(key)


def catalog_public() -> list[dict[str, Any]]:
    return [
        {
            "key": a.key,
            "tier": a.tier,
            "description": a.description,
            "notes": a.notes,
            "planner_only": a.planner_only,
        }
        for a in ACTIONS.values()
    ]
