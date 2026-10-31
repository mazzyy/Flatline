"""Dashboard pages exist and claim only implemented surfaces."""

from __future__ import annotations

from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "dashboard" / "src"


def test_all_pages_present() -> None:
    for name in ("Overview.tsx", "Incident.tsx", "Transactions.tsx", "Policy.tsx", "Audit.tsx", "Chaos.tsx"):
        assert (SRC / "pages" / name).exists(), name


def test_ag_grid_and_sse() -> None:
    tx = (SRC / "pages" / "Transactions.tsx").read_text()
    assert "rowModelType" in tx
    assert "simulated" in tx.lower()
    app = (SRC / "App.tsx").read_text()
    assert "EventSource" in app
    assert "/api/stream" in app
