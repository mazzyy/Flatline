"""Load YAML playbook definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PLAYBOOK_DIR = Path(__file__).resolve().parent


@dataclass
class Playbook:
    name: str
    metric: str
    window_minutes: int
    multiplier: float
    min_count: int
    baseline_floor: float
    scope_key: str = "none"
    evidence: list[str] = field(default_factory=list)
    allowed_actions: list[str] = field(default_factory=list)
    enabled: bool = True
    average_order_value: float = 18.0
    plan_price: float = 14.0
    concentration_ratio: float = 0.5
    reconcile_lag_hours: int = 3
    raw: dict[str, Any] = field(default_factory=dict)


def load_playbooks(directory: Path | None = None) -> dict[str, Playbook]:
    directory = directory or PLAYBOOK_DIR
    out: dict[str, Playbook] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        name = str(data.get("name") or path.stem)
        out[name] = Playbook(
            name=name,
            metric=str(data.get("metric") or name),
            window_minutes=int(data.get("window_minutes") or 5),
            multiplier=float(data.get("multiplier") or 3),
            min_count=int(data.get("min_count") or 1),
            baseline_floor=float(data.get("baseline_floor") or 0),
            scope_key=str(data.get("scope_key") or "none"),
            evidence=list(data.get("evidence") or []),
            allowed_actions=list(data.get("allowed_actions") or []),
            enabled=bool(data.get("enabled", True)),
            average_order_value=float(data.get("average_order_value") or 18),
            plan_price=float(data.get("plan_price") or 14),
            concentration_ratio=float(data.get("concentration_ratio") or 0.5),
            reconcile_lag_hours=int(data.get("reconcile_lag_hours") or 3),
            raw=data,
        )
    return out
