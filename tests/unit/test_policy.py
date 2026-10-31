"""Policy proxy: every catalog key, unknowns, refund cap, rate limits."""

from __future__ import annotations

from flatline.policy.catalog import ACTIONS
from flatline.policy.proxy import decide, rate_limit_auto, rate_limit_pending


def test_every_catalog_key_has_a_decision() -> None:
    for key, spec in ACTIONS.items():
        result = decide(key, {"amount": 1})
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


def test_auto_can_be_disabled() -> None:
    result = decide("notify.alert", {}, auto_enabled=False)
    assert result.tier == "approval"


def test_rate_limits() -> None:
    assert rate_limit_auto(4) is True
    assert rate_limit_auto(5) is False
    assert rate_limit_pending(0) is True
    assert rate_limit_pending(1) is False
