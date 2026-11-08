"""Live model calls: real input in the prompt, honest labels, safe fallback."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from flatline.agents import nodes
from flatline.agents.schemas import TriageOutput, VerifierOutput
from flatline.config import reset_settings, settings
from flatline.db.models import Incident
from flatline.llm import models
from flatline.llm.mock_llm import triage

INCIDENT = {
    "id": "inc-1",
    "playbook": "checkout_failure_spike",
    "observed_value": 6,
    "baseline_value": 1,
    "revenue_at_risk_per_hour": 108.0,
    "scope_key": "currency",
    "scope_value": "EUR",
}
EVENTS = [{"id": "e1", "error_code": "CURRENCY_MISMATCH", "currency": "EUR"}]


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("MODEL_FAST", "gemini/test-fast")
    reset_settings()


def _draft() -> TriageOutput:
    return triage(INCIDENT, EVENTS)


def test_mock_mode_never_calls_a_model(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: object, **_k: object) -> str:
        raise AssertionError("no model call in mock mode")

    monkeypatch.setattr(models, "live_complete", boom)
    draft = _draft()
    out, label = nodes._ask_model("triage", "fast", {"incident": INCIDENT}, draft)
    assert out == draft
    assert label == "mock"


def test_live_answer_is_used_and_credited(live: None, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}
    answer = _draft().model_copy(update={"severity": "critical"})

    def fake(model: str, prompt: str, **_k: object) -> str:
        seen["model"], seen["prompt"] = model, prompt
        return answer.model_dump_json()

    monkeypatch.setattr(models, "live_complete", fake)
    out, label = nodes._ask_model(
        "triage", "fast", {"incident": INCIDENT, "events": EVENTS}, _draft()
    )
    assert out.severity == "critical"
    assert label == "gemini/test-fast" == settings().model_fast
    assert "CURRENCY_MISMATCH" in seen["prompt"]  # the real input reaches the model
    assert '"title": "TriageOutput"' in seen["prompt"]  # and the output schema
    assert _draft().summary not in seen["prompt"]  # but never the playbook's answer


@pytest.mark.parametrize("reply", [RuntimeError("429 quota"), "not json at all"])
def test_failure_keeps_the_draft_and_says_so(
    live: None, monkeypatch: pytest.MonkeyPatch, reply: object
) -> None:
    def fake(*_a: object, **_k: object) -> str:
        if isinstance(reply, Exception):
            raise reply
        return str(reply)

    monkeypatch.setattr(models, "live_complete", fake)
    draft = _draft()
    out, label = nodes._ask_model("triage", "fast", {"incident": INCIDENT}, draft)
    assert out == draft
    assert label == "gemini/test-fast (failed, playbook fallback)"


def test_verifier_model_cannot_flip_the_metric_decision(
    live: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    flipped = VerifierOutput(resolved=True, observation="looks fine", next_step="close")
    monkeypatch.setattr(models, "live_complete", lambda *_a, **_k: flipped.model_dump_json())
    incident = Incident(id=uuid.uuid4(), playbook="checkout_failure_spike", status="verifying")
    out = nodes.run_verifier(MagicMock(), incident, False, "failures still above baseline")
    assert out.resolved is False  # the metric decides
    assert out.observation == "looks fine"  # the model writes the words
    assert incident.status == "verifying"


def test_provider_keys_reach_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_API_BASE", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")
    reset_settings()
    cfg = settings()
    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.delenv("OLLAMA_API_BASE")
    models.configure_litellm_env(cfg)
    import os

    assert os.environ["GEMINI_API_KEY"] == "k"
    assert os.environ["OLLAMA_API_BASE"] == "http://localhost:11434"


def test_a_429_moves_on_to_the_next_model(live: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_FALLBACKS", "gemini/test-fast, gemini/backup")
    reset_settings()
    tried: list[str] = []
    answer = _draft().model_copy(update={"severity": "critical"})

    def fake(model: str, prompt: str, **_k: object) -> str:
        tried.append(model)
        if model == "gemini/test-fast":
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "```json\n" + answer.model_dump_json() + "\n```"  # fenced, still parsed

    monkeypatch.setattr(models, "live_complete", fake)
    out, label = nodes._ask_model("triage", "fast", {"incident": INCIDENT}, _draft())
    assert tried == ["gemini/test-fast", "gemini/backup"]  # the primary is not tried twice
    assert out.severity == "critical"
    assert label == "gemini/backup"  # credited to the model that answered


def test_remediator_sees_the_allowed_actions(live: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from flatline.agents.schemas import DiagnosisOutput
    from flatline.llm.mock_llm import remediate

    monkeypatch.setenv("MODEL_REASONING", "gemini/test-reasoning")
    reset_settings()
    seen: dict[str, str] = {}
    body = {"id": "inc-1", "playbook": "subscription_renewal_failures", "scope_value": "P-1"}
    diagnosis = DiagnosisOutput.model_validate(
        {
            "root_cause": "renewals fail",
            "confidence": 0.8,
            "evidence": [{"claim": "4 failed renewals", "source": "events", "ref": "e1"}],
        }
    )

    def fake(model: str, prompt: str, **_k: object) -> str:
        seen["prompt"] = prompt
        return remediate(body, diagnosis).model_dump_json()

    monkeypatch.setattr(models, "live_complete", fake)
    incident = Incident(id=uuid.uuid4(), playbook="subscription_renewal_failures", status="open")
    incident.scope_value = "P-1"
    nodes.run_remediator(MagicMock(), incident, diagnosis)
    assert "invoice.send_reminder" in seen["prompt"]
    assert "allowed_actions" in seen["prompt"]


def test_agents_never_see_the_test_harness(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chaos flags, injected markers and chaos-only versions stay out of the agents' view."""
    from flatline.agents import tools
    from flatline.agents.workflow import _event_dicts
    from flatline.db.base import utcnow
    from flatline.db.models import Event, ShopConfigVersion
    from flatline.db.session import create_schema, get_sessionmaker, reset_engine

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/view.db")
    reset_engine()
    create_schema()
    db = get_sessionmaker()()
    base = {"currency": "USD", "banner": ""}
    rows = [
        (1, base, "seed"),
        (2, {**base, "chaos": {"inject": "refund_wave"}}, "live check: refund_wave"),
        (
            3,
            {**base, "currency": "EUR", "chaos": {"bad_currency": True}},
            "Storefront currency set to EUR",
        ),
    ]
    for version, config, note in rows:
        db.add(
            ShopConfigVersion(
                version=version, config=config, author="human", note=note, active=version == 3
            )
        )
    db.add(
        Event(
            source="synthetic", event_type="checkout.capture", occurred_at=utcnow(), synthetic=True
        )
    )
    db.commit()

    history = tools.config_history(db)
    assert [h["version"] for h in history] == [1, 3]  # the chaos-only version is folded in
    assert all("chaos" not in h["config"] for h in history)
    assert "live check" not in str(history)
    assert history[-1]["active"] and history[-1]["config"]["currency"] == "EUR"
    events = _event_dicts(list(db.query(Event).all()))
    assert "synthetic" not in events[0]
    db.close()
    reset_engine()


def test_each_incident_only_sees_its_own_events(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Earlier checkout failures must not leak into a refund wave's evidence."""
    from datetime import timedelta

    from flatline.agents import tools
    from flatline.db.base import utcnow
    from flatline.db.models import Event
    from flatline.db.session import create_schema, get_sessionmaker, reset_engine

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/scope.db")
    reset_engine()
    create_schema()
    db = get_sessionmaker()()
    now = utcnow()
    for _ in range(6):
        db.add(
            Event(
                source="t",
                event_type="checkout.capture",
                error_code="CURRENCY_MISMATCH",
                currency="EUR",
                occurred_at=now,
            )
        )
    for product in ["ethiopia-yirgacheffe"] * 5 + ["house-blend"]:
        db.add(
            Event(
                source="t",
                event_type="PAYMENT.CAPTURE.REFUNDED",
                product_id=product,
                occurred_at=now,
            )
        )
    db.commit()
    wave = Incident(id=uuid.uuid4(), playbook="refund_wave", status="open", metric="refunds")
    wave.scope_key, wave.scope_value = "product_id", "ethiopia-yirgacheffe"
    wave.window_start = now - timedelta(minutes=60)
    events, background = tools.incident_events(db, wave)
    assert len(events) == 5
    assert {e.product_id for e in events} == {"ethiopia-yirgacheffe"}
    grouped = tools.events_by_group(events, background)
    assert "CURRENCY_MISMATCH" not in grouped["error_code_breakdown"]
    assert grouped["other_traffic_in_window"]["checkout.capture"] == 6  # counted, not detailed
    db.close()
    reset_engine()
