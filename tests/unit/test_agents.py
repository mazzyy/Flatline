"""Mock-LLM checkout diagnosis and evidence schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from flatline.agents.schemas import DiagnosisOutput, EvidenceClaim
from flatline.llm.mock_llm import diagnose, remediate


def test_evidence_required() -> None:
    with pytest.raises(ValidationError):
        DiagnosisOutput(root_cause="guess", confidence=0.9, evidence=[])


def test_checkout_currency_diagnosis() -> None:
    incident = {"playbook": "checkout_failure_spike", "id": "x"}
    events = [
        {"id": "e1", "error_code": "CURRENCY_MISMATCH", "currency": "EUR", "resource_id": "ORD-1"}
    ]
    history = [
        {
            "version": 2,
            "active": True,
            "config": {"currency": "EUR", "chaos": {"bad_currency": True}},
        }
    ]
    out = diagnose(incident, events, history, {})
    assert "config version" in out.root_cause.lower()
    assert out.evidence
    props = remediate(incident, out)
    actions = [p.action for p in props.proposals]
    assert "shop.config.rollback" in actions
    assert "shop.banner.set" in actions


def test_checkout_declines_no_rollback() -> None:
    incident = {"playbook": "checkout_failure_spike", "id": "x"}
    events = [
        {
            "id": f"e{i}",
            "error_code": "INSTRUMENT_DECLINED",
            "buyer_ref": f"B{i}",
            "currency": "USD",
        }
        for i in range(6)
    ]
    history = [{"version": 1, "active": True, "config": {"currency": "USD", "chaos": {}}}]
    out = diagnose(incident, events, history, {})
    assert "declin" in out.root_cause.lower()
    actions = [p.action for p in remediate(incident, out).proposals]
    assert "shop.config.rollback" not in actions


def test_bulk_refund_is_a_labelled_red_team_probe_not_a_model_answer() -> None:
    import uuid

    from flatline.db.models import Incident
    from flatline.loop import red_team_probe

    incident = {"playbook": "refund_wave", "scope_value": "ethiopia-yirgacheffe", "id": "x"}
    out = diagnose(incident, [{"id": "r1"}], [], {})
    assert "ethiopia" in out.root_cause
    actions = [p.action for p in remediate(incident, out).proposals]
    assert "shop.product.pause_sales" in actions
    assert "refund.bulk" not in actions  # no answer of the remediator contains it

    row = Incident(id=uuid.uuid4(), playbook="refund_wave", status="open")
    row.scope_key, row.scope_value = "product_id", "ethiopia-yirgacheffe"
    probe = red_team_probe(row)
    assert probe is not None and probe.action == "refund.bulk"
    assert "Red-team probe added by the playbook, not by the model" in probe.rationale
    row.playbook = "checkout_failure_spike"
    assert red_team_probe(row) is None


def test_evidence_claim_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        EvidenceClaim(claim="x", source="", ref="1")
