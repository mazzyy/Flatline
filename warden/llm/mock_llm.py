"""Deterministic, playbook-aware stub used when LLM_MODE=mock."""

from __future__ import annotations

from typing import Any

from warden.agents.schemas import (
    DiagnosisOutput,
    EvidenceClaim,
    ProposalDraft,
    RemediatorOutput,
    Severity,
    TriageOutput,
    VerifierOutput,
)


def triage(incident: dict[str, Any], events: list[dict[str, Any]]) -> TriageOutput:
    observed = float(incident.get("observed_value") or 0)
    severity: Severity = "critical" if observed >= 10 else "high" if observed >= 5 else "med"
    return TriageOutput(
        playbook_confirmed=True,
        severity=severity,
        scope={"key": incident.get("scope_key"), "value": incident.get("scope_value")},
        revenue_at_risk_per_hour=float(incident.get("revenue_at_risk_per_hour") or 0),
        summary=f"{incident.get('playbook')} is real: {int(observed)} against baseline "
        f"{incident.get('baseline_value')}.",
    )


def _codes(events: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for event in events:
        code = event.get("error_code") or event.get("event_type")
        if code:
            out[str(code)] = out.get(str(code), 0) + 1
    return out


def diagnose(
    incident: dict[str, Any],
    events: list[dict[str, Any]],
    config_history: list[dict[str, Any]],
    tool_bundle: dict[str, Any],
) -> DiagnosisOutput:
    playbook = incident.get("playbook")
    codes = _codes(events)
    active = next((c for c in config_history if c.get("active")), config_history[-1] if config_history else {})
    config = (active.get("config") or {}) if active else {}
    chaos = config.get("chaos") or {}

    if playbook == "checkout_failure_spike":
        currency_bad = (
            bool(chaos.get("bad_currency"))
            or config.get("currency") not in (None, "USD")
            or "CURRENCY_MISMATCH" in codes
            or any((e.get("currency") and e.get("currency") != "USD") for e in events)
        )
        sample = events[0] if events else {}
        if currency_bad:
            version = active.get("version") or tool_bundle.get("bad_version") or 2
            return DiagnosisOutput(
                root_cause=(
                    f"Shop config version {version} introduced the wrong currency, so captures fail."
                ),
                confidence=0.92,
                evidence=[
                    EvidenceClaim(
                        claim=f"active config version {version} has currency={config.get('currency')!s} chaos={chaos}",
                        source="config",
                        ref=str(version),
                    ),
                    EvidenceClaim(
                        claim=f"sample failing order {sample.get('resource_id') or sample.get('id') or 'n/a'}",
                        source="event",
                        ref=str(sample.get("id") or sample.get("resource_id") or "event"),
                    ),
                ],
                hypotheses_rejected=["buyer-side card declines as the primary cause"],
            )
        buyers = {e.get("buyer_ref") for e in events if e.get("buyer_ref")}
        return DiagnosisOutput(
            root_cause=(
                "Buyer-side declines (INSTRUMENT_DECLINED) across many distinct buyers; "
                "not a merchant config regression."
            ),
            confidence=0.88,
            evidence=[
                EvidenceClaim(
                    claim=f"{len(buyers)} distinct buyers declined",
                    source="event",
                    ref=",".join(sorted(str(b) for b in buyers)[:8]) or "buyers",
                ),
                EvidenceClaim(
                    claim=f"error codes {codes}",
                    source="event",
                    ref="error_code_breakdown",
                ),
            ],
            hypotheses_rejected=["a bad shop config deploy"],
        )

    if playbook == "refund_wave":
        product = incident.get("scope_value") or "ethiopia-yirgacheffe"
        return DiagnosisOutput(
            root_cause=f"Refunds are concentrated on product {product}.",
            confidence=0.9,
            evidence=[
                EvidenceClaim(claim=f"scope product {product}", source="incident", ref=str(incident.get("id"))),
                EvidenceClaim(claim=f"{len(events)} refund events in window", source="event", ref="refunds"),
            ],
            hypotheses_rejected=["random buyer remorse spread across the catalog"],
        )

    if playbook == "subscription_renewal_failures":
        plan = incident.get("scope_value") or "P-COFFEECLUB"
        return DiagnosisOutput(
            root_cause=f"Subscription renewals are failing on plan {plan}.",
            confidence=0.86,
            evidence=[
                EvidenceClaim(claim=f"plan {plan} failed renewals", source="event", ref=plan),
                EvidenceClaim(claim="failed PAYMENT events clustered on one plan", source="event", ref="renewals"),
            ],
            hypotheses_rejected=["a checkout capture outage"],
        )

    return DiagnosisOutput(
        root_cause="Insufficient evidence for a specific merchant-side cause.",
        confidence=0.4,
        evidence=[EvidenceClaim(claim="generic fallback", source="incident", ref=str(incident.get("id")))],
        hypotheses_rejected=[],
    )


def remediate(incident: dict[str, Any], diagnosis: DiagnosisOutput) -> RemediatorOutput:
    playbook = incident.get("playbook")
    if playbook == "checkout_failure_spike":
        if "currency" in diagnosis.root_cause.lower() or "config version" in diagnosis.root_cause.lower():
            return RemediatorOutput(
                proposals=[
                    ProposalDraft(
                        action="notify.alert",
                        params={"message": diagnosis.root_cause},
                        rationale="Page the merchant immediately.",
                        expected_effect="human is notified",
                    ),
                    ProposalDraft(
                        action="shop.banner.set",
                        params={"text": "Checkout is being repaired. Cards have not been charged."},
                        rationale="Honest banner while we roll back.",
                        expected_effect="shoppers see a status banner",
                    ),
                    ProposalDraft(
                        action="shop.config.rollback",
                        params={"version": None},
                        rationale="Restore the last good currency config.",
                        expected_effect="captures succeed again",
                    ),
                ]
            )
        return RemediatorOutput(
            proposals=[
                ProposalDraft(
                    action="notify.alert",
                    params={"message": diagnosis.root_cause},
                    rationale="Issuer declines, not our config.",
                    expected_effect="merchant is aware",
                ),
                ProposalDraft(
                    action="shop.banner.set",
                    params={"text": "Some cards are being declined by the issuer. Try another card."},
                    rationale="Set expectations; do not roll back a healthy config.",
                    expected_effect="shoppers see guidance",
                ),
            ]
        )
    if playbook == "refund_wave":
        product = incident.get("scope_value") or "ethiopia-yirgacheffe"
        return RemediatorOutput(
            proposals=[
                ProposalDraft(
                    action="notify.alert",
                    params={"message": diagnosis.root_cause},
                    rationale="Refund wave needs a human in the loop.",
                    expected_effect="alert",
                ),
                ProposalDraft(
                    action="report.create",
                    params={"markdown": f"# Refund wave\n\nProduct `{product}`."},
                    rationale="Write down the evidence.",
                    expected_effect="report attached",
                ),
                ProposalDraft(
                    action="shop.product.pause_sales",
                    params={"product_id": product},
                    rationale="Stop selling the implicated product.",
                    expected_effect="product paused",
                ),
                ProposalDraft(
                    action="refund.bulk",
                    params={"product_id": product},
                    rationale="Agent temptation: bulk-refund the rest. Policy must refuse.",
                    expected_effect="should be refused",
                ),
            ]
        )
    if playbook == "subscription_renewal_failures":
        return RemediatorOutput(
            proposals=[
                ProposalDraft(
                    action="notify.alert",
                    params={"message": diagnosis.root_cause},
                    rationale="Renewals are failing.",
                    expected_effect="alert",
                ),
                ProposalDraft(
                    action="invoice.send_reminder",
                    params={"invoice_id": "INV-OUTSTANDING", "subscription_id": "I-COFFEECLUB-1"},
                    rationale="Remind the subscriber.",
                    expected_effect="reminder sent",
                ),
                ProposalDraft(
                    action="subscription.capture_outstanding",
                    params={"subscription_id": "I-COFFEECLUB-1"},
                    rationale="Retry the outstanding balance.",
                    expected_effect="capture attempted",
                ),
            ]
        )
    return RemediatorOutput(proposals=[])


def verify(resolved: bool, observation: str) -> VerifierOutput:
    return VerifierOutput(
        resolved=resolved,
        observation=observation,
        next_step="close" if resolved else "keep watching and escalate if it repeats",
    )
