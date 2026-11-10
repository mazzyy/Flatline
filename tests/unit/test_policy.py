"""Policy proxy: every catalog key, unknowns, money limits, rate limits."""

from __future__ import annotations

from flatline.policy.catalog import ACTIONS
from flatline.policy.proxy import PLANNER, decide, items_total, rate_limit_auto, rate_limit_pending

ITEMS = {"items": [{"event_id": "e1", "amount": "18.00"}, {"event_id": "e2", "amount": "18.00"}]}


def test_every_catalog_key_has_a_decision() -> None:
    for key, spec in ACTIONS.items():
        source = PLANNER if spec.planner_only else "agent"
        result = decide(key, {"amount": 1, **ITEMS}, source=source)
        assert result.tier == spec.tier or (
            key == "refund.single" and result.tier in {"approval", "forbidden"}
        )


def test_unknown_action_is_forbidden() -> None:
    result = decide("payout.drain", {})
    assert result.tier == "forbidden"
    assert "not in the action catalog" in result.reason


def test_explicit_forbidden() -> None:
    assert decide("refund.bulk", {}).tier == "forbidden"
    assert decide("subscription.cancel", {}).tier == "forbidden"
    assert decide("dispute.accept", {}).tier == "forbidden"


def test_refund_over_cap_is_forbidden() -> None:
    result = decide("refund.single", {"amount": 80}, refund_max=50)
    assert result.tier == "forbidden"
    result = decide("refund.single", {"amount": 20}, refund_max=50)
    assert result.tier == "approval"


def test_no_refund_runs_on_its_own_by_default() -> None:
    # AUTO_REFUND_MAX is 0 unless the merchant sets it: money waits for a person.
    assert decide("refund.single", {"amount": 0.01}).tier == "approval"
    assert decide("refund.single", {"amount": 5}).tier == "approval"


def test_small_refund_is_auto_only_when_the_merchant_opts_in() -> None:
    assert decide("refund.single", {"amount": 15}, auto_refund_max=20).tier == "auto"
    assert decide("refund.single", {"amount": 20}, auto_refund_max=20).tier == "auto"
    assert decide("refund.single", {"amount": 20.01}, auto_refund_max=20).tier == "approval"
    # The automatic limit can never reach past the approval limit.
    assert decide("refund.single", {"amount": 60}, auto_refund_max=500).tier == "forbidden"
    # Switching auto actions off switches automatic refunds off too.
    off = decide("refund.single", {"amount": 15}, auto_refund_max=20, auto_enabled=False)
    assert off.tier == "approval"
    # No amount, no automatic refund.
    assert decide("refund.single", {}, auto_refund_max=20).tier == "approval"


def test_daily_refund_budget() -> None:
    inside = decide("refund.single", {"amount": 30}, refunded_today=160, daily_refund_budget=200)
    assert inside.tier == "approval"
    over = decide("refund.single", {"amount": 30}, refunded_today=180, daily_refund_budget=200)
    assert over.tier == "forbidden"
    assert "DAILY_REFUND_BUDGET" in over.reason
    # The budget stops automatic refunds as well.
    auto = decide(
        "refund.single",
        {"amount": 15},
        auto_refund_max=20,
        refunded_today=190,
        daily_refund_budget=200,
    )
    assert auto.tier == "forbidden"


def test_an_agent_cannot_propose_recovery() -> None:
    for action in ("recovery.payment_links.send", "recovery.renewals.retry"):
        from_agent = decide(action, ITEMS)
        assert from_agent.tier == "forbidden"
        assert "planned by code" in from_agent.reason
        assert decide(action, ITEMS, source=PLANNER).tier == "approval"


def test_recovery_is_capped_and_the_proxy_adds_the_items_up_itself() -> None:
    assert items_total({"items": ITEMS["items"], "total": "1.00"}) == (2, 36.0)
    empty = decide("recovery.payment_links.send", {"items": []}, source=PLANNER)
    assert empty.tier == "forbidden"
    many = {"items": [{"event_id": str(i), "amount": "1.00"} for i in range(26)]}
    assert decide("recovery.payment_links.send", many, source=PLANNER).tier == "forbidden"
    # A small `total` field does not get a large batch past the cap.
    large = {"items": [{"event_id": "e", "amount": "600.00"}] * 2, "total": "10.00"}
    refused = decide("recovery.payment_links.send", large, source=PLANNER)
    assert refused.tier == "forbidden"
    assert "RECOVERY_MAX_TOTAL" in refused.reason


def test_auto_can_be_disabled() -> None:
    result = decide("notify.alert", {}, auto_enabled=False)
    assert result.tier == "approval"


def test_rate_limits() -> None:
    assert rate_limit_auto(4) is True
    assert rate_limit_auto(5) is False
    assert rate_limit_pending(0) is True
    assert rate_limit_pending(1) is False
