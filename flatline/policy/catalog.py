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


ACTIONS: dict[str, ActionSpec] = {
    "notify.alert": ActionSpec(
        "notify.alert", "auto", "Log an alert and optionally POST NOTIFY_WEBHOOK_URL"
    ),
    "report.create": ActionSpec(
        "report.create", "auto", "Attach a markdown report to the incident"
    ),
    "shop.banner.set": ActionSpec("shop.banner.set", "auto", "Set the shop-wide banner"),
    "shop.banner.clear": ActionSpec("shop.banner.clear", "auto", "Clear the shop-wide banner"),
    "invoice.send_reminder": ActionSpec(
        "invoice.send_reminder", "auto", "Send a reminder to one subscriber"
    ),
    "shop.config.rollback": ActionSpec(
        "shop.config.rollback", "approval", "Activate a previous shop config version"
    ),
    "shop.product.pause_sales": ActionSpec(
        "shop.product.pause_sales", "approval", "Pause sales of one product"
    ),
    "shop.product.resume_sales": ActionSpec(
        "shop.product.resume_sales", "approval", "Resume sales of one product"
    ),
    "shop.plan.pause_signups": ActionSpec(
        "shop.plan.pause_signups", "approval", "Pause new sign-ups on a plan"
    ),
    "shop.plan.resume_signups": ActionSpec(
        "shop.plan.resume_signups", "approval", "Resume plan sign-ups"
    ),
    "subscription.capture_outstanding": ActionSpec(
        "subscription.capture_outstanding", "approval", "Capture outstanding balance via REST"
    ),
    "subscription.suspend": ActionSpec(
        "subscription.suspend", "approval", "Suspend one subscription"
    ),
    "subscription.activate": ActionSpec(
        "subscription.activate", "approval", "Activate one subscription"
    ),
    "refund.single": ActionSpec(
        "refund.single", "approval", "Refund one capture if amount ≤ REFUND_APPROVAL_MAX"
    ),
    "events.replay": ActionSpec("events.replay", "approval", "Replay missing webhook events"),
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
        {"key": a.key, "tier": a.tier, "description": a.description, "notes": a.notes}
        for a in ACTIONS.values()
    ]
