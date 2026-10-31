"""Dashboard pages exist and claim only implemented surfaces."""

from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "dashboard" / "src"


def test_all_pages_present() -> None:
    for name in (
        "Overview.tsx",
        "Incident.tsx",
        "Transactions.tsx",
        "Policy.tsx",
        "Audit.tsx",
        "Chaos.tsx",
        "HowItWorks.tsx",
    ):
        assert (SRC / "pages" / name).exists(), name


def test_how_it_works_explains_the_loop() -> None:
    how = (SRC / "pages" / "HowItWorks.tsx").read_text()
    for word in ("Detect", "Diagnose", "Propose", "Gate", "Execute", "Verify"):
        assert word in how, word
    assert "forbidden" in how.lower()
    app = (SRC / "App.tsx").read_text()
    assert "How it works" in app


def test_ag_grid_and_sse() -> None:
    tx = (SRC / "pages" / "Transactions.tsx").read_text()
    assert "rowModelType" in tx
    assert "simulated" in tx.lower()
    app = (SRC / "App.tsx").read_text()
    assert "EventSource" in app
    assert "/api/stream" in app
