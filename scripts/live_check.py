#!/usr/bin/env python3
"""End to end check of a running stack: real sandbox, live models, all three scenarios.

    make up                                   # with LLM_MODE=live and PAYPAL_ENVIRONMENT=SANDBOX
    python scripts/live_check.py              # http://localhost:8000, passcode and token from .env
    python scripts/live_check.py --url https://<your-api>.onrender.com

For each scenario it presses the same Chaos button as the dashboard, waits for
the agents, and prints every step with its model, latency and PayPal reads (MCP
or REST). It approves the checkout rollback, then resets all chaos. Exits 1 when
a check fails, so a run that ends in PASS is safe to record.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

import httpx

from flatline.config import settings

SCENARIOS = [
    ("checkout_failure_spike", "Ship bad currency config", {"bad_currency": True}),
    ("refund_wave", "Inject refund wave", {"inject": "refund_wave"}),
    (
        "subscription_renewal_failures",
        "Inject subscription renewal failures",
        {"inject": "renewal_failures"},
    ),
]
WAIT_S = 300


class Report:
    def __init__(self) -> None:
        self.failed: list[str] = []

    def check(self, ok: bool, label: str) -> None:
        print(f"    {'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            self.failed.append(label)


def wait_for_agents(api: httpx.Client, incident_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + WAIT_S
    while True:
        body: dict[str, Any] = api.get(f"/api/incidents/{incident_id}").json()
        if body.get("proposals"):
            return body
        if time.monotonic() > deadline:
            raise TimeoutError(f"agents did not finish incident {incident_id} in {WAIT_S}s")
        time.sleep(3)


def find_incident(api: httpx.Client, playbook: str, touched: list[str]) -> str:
    items = api.get("/api/incidents", params={"playbook": playbook}).json()["items"]
    for item in items:
        if item["id"] in touched or item["status"] != "resolved":
            return str(item["id"])
    raise RuntimeError(f"no incident opened for {playbook}")


def show_steps(body: dict[str, Any], report: Report) -> None:
    reads = []
    for step in sorted(body.get("steps", []), key=lambda s: s["created_at"]):
        model = str(step.get("model") or "")
        print(f"    {step['node']:14s} {model:45s} {step.get('latency_ms', 0):>6} ms")
        report.check(
            model not in ("", "mock") and "failed" not in model,
            f"{step['node']} answered by a live model",
        )
        for call in step.get("tool_calls") or []:
            if isinstance(call, dict) and call.get("via"):
                reads.append(call)
    for call in reads:
        extra = f" ({call['mcp_error'][:120]})" if call.get("mcp_error") else ""
        print(f"    PayPal read   {call['tool']:35s} via {call['via']}{extra}")
    report.check(any(c["via"] == "mcp" for c in reads), "PayPal read through the MCP server")


def show_proposals(body: dict[str, Any]) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = body.get("proposals", [])
    for p in proposals:
        print(f"    proposal      {p['action']:35s} {p['tier']:9s} {p['status']}")
    return proposals


def main() -> int:
    cfg = settings()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--passcode", default=cfg.dashboard_passcode)
    parser.add_argument("--token", default=cfg.inject_token)
    args = parser.parse_args()

    api = httpx.Client(
        base_url=args.url.rstrip("/"),
        headers={"x-passcode": args.passcode, "x-inject-token": args.token},
        timeout=60,
    )
    report = Report()
    health = api.get("/healthz").json()
    print(f"{args.url}: PayPal {health['paypal_environment']}, models {health['llm_mode']}")
    report.check(health["paypal_environment"] == "SANDBOX", "PayPal sandbox, not mock")
    report.check(health["llm_mode"] == "live", "LLM_MODE=live")

    api.post("/api/chaos", json={"reset": True, "note": "live check"}).raise_for_status()
    for playbook, label, chaos in SCENARIOS:
        print(f"\n{label}")
        started = time.monotonic()
        resp = api.post("/api/chaos", json={"chaos": chaos, "note": f"live check: {playbook}"})
        resp.raise_for_status()
        incident_id = find_incident(api, playbook, resp.json().get("incidents", []))
        body = wait_for_agents(api, incident_id)
        print(
            f"    incident {incident_id}: {body['status']}, agents took {time.monotonic() - started:.0f}s"
        )
        print(f"    root cause: {(body.get('root_cause') or '')[:160]}")
        show_steps(body, report)
        proposals = show_proposals(body)

        if playbook == "checkout_failure_spike":
            pending = [p for p in proposals if p["status"] == "pending"]
            earlier = [
                p for p in proposals if p["tier"] == "approval" and p["status"] == "executed"
            ]
            if earlier and not pending:
                print(
                    "    (this incident was opened and approved by an earlier run in the last 30 min)"
                )
            report.check(bool(pending or earlier), "a fix waits for approval")
            for p in pending[:1]:
                done = api.post(f"/api/proposals/{p['id']}/approve").json()
                after = api.get(f"/api/incidents/{incident_id}").json()
                print(
                    f"    approved {p['action']}: {done['status']}; incident now {after['status']}"
                )
                report.check(done["status"] in ("approved", "executed"), "approval executes")
        elif playbook == "refund_wave":
            report.check(
                any(p["status"] == "refused" for p in proposals), "the bulk refund is refused"
            )
        else:
            report.check(
                any(
                    p["tier"] == "auto" and p["status"] in ("approved", "executed")
                    for p in proposals
                ),
                "the reminder runs on its own",
            )
            report.check(
                any(p["status"] == "pending" for p in proposals), "the capture waits for approval"
            )

    api.post("/api/chaos", json={"reset": True, "note": "live check done"}).raise_for_status()
    print("\nchaos reset")
    if report.failed:
        print(f"\nFAILED: {len(report.failed)} checks")
        for label in report.failed:
            print(f"  {label}")
        return 1
    print("\nPASS: everything above ran against the PayPal sandbox with live models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
