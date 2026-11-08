"""Hosted mode: one service runs the API, the detector and the agent loop."""

from __future__ import annotations

import threading

import pytest

import flatline.detector.worker as detector
import flatline.loop as agents
from flatline.ingest import app as app_module


def test_run_workers_starts_both_loops(monkeypatch: pytest.MonkeyPatch) -> None:
    started: list[str] = []
    monkeypatch.setattr(detector, "run_forever", lambda: started.append("detector"))
    monkeypatch.setattr(agents, "run_forever", lambda: started.append("agents"))
    app_module._start_workers()
    for thread in threading.enumerate():
        if thread.name in ("flatline-detector", "flatline-agents"):
            assert thread.daemon  # never blocks shutdown
            thread.join(timeout=2)
    assert sorted(started) == ["agents", "detector"]
