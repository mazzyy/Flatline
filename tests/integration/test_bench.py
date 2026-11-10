"""The benchmark runs clean with the deterministic stand ins, and never leaves the mock."""

from __future__ import annotations

import json
import sys

import pytest

from flatline import bench
from flatline.db.session import reset_engine

ENV = ("PAYPAL_ENVIRONMENT", "LLM_MODE", "DEMO_MODE", "VERIFY_MINUTES", "DATABASE_URL")


def test_benchmark_passes_every_check(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV:  # the benchmark sets these itself; put them back afterwards
        monkeypatch.setenv(key, "")
    # Even with a sandbox .env, the benchmark must not reach a PayPal account.
    monkeypatch.setenv("PAYPAL_ENVIRONMENT", "SANDBOX")
    out = tmp_path / "bench.json"
    monkeypatch.setattr(sys, "argv", ["bench", "--json", str(out)])
    try:
        assert bench.main() == 0
    finally:
        reset_engine()
    body = json.loads(out.read_text())
    incidents = [r for r in body["results"] if not r["control"]]
    assert len(incidents) == 5 and len(body["results"]) == 7
    for row in body["results"]:
        assert all(row["checks"].values()), row
    assert all(p["passed"] for p in body["probes"])
    by_key = {r["key"]: r for r in incidents}
    assert by_key["bad_currency"]["asked_back"] == "108.00"
    assert by_key["issuer_declines"]["asked_back"] == "0.00"  # a declined card is left alone
    assert by_key["refund_wave"]["lost"] == "110.00"
    assert {m for r in incidents for m in r["models"]} == {"mock", "code, no model"}
