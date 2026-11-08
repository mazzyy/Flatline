#!/usr/bin/env python3
"""Inject one playbook fault through the API, exactly like the Chaos panel button.

    python scripts/inject.py checkout_failure_spike
    python scripts/inject.py refund_wave
    python scripts/inject.py subscription_renewal_failures

The server writes the labelled synthetic events (flatline/ingest/faults.py) and
runs the detector straight away.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # run from anywhere

import httpx

from flatline.config import apply_sandbox_guard, settings

CHAOS = {
    "checkout_failure_spike": {"bad_currency": True},
    "refund_wave": {"inject": "refund_wave"},
    "subscription_renewal_failures": {"inject": "renewal_failures"},
}


def main() -> int:
    apply_sandbox_guard()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("playbook", choices=sorted(CHAOS))
    args = parser.parse_args()
    cfg = settings()
    base = os.environ.get("FLATLINE_API_URL", cfg.app_base_url)
    headers = {"X-Inject-Token": cfg.inject_token, "X-Passcode": cfg.dashboard_passcode}
    resp = httpx.post(
        f"{base}/api/chaos",
        headers=headers,
        json={"chaos": CHAOS[args.playbook], "note": f"inject.py {args.playbook}"},
        timeout=20,
    )
    resp.raise_for_status()
    body = resp.json()
    print(
        f"injected {args.playbook}: {len(body.get('injected', []))} events, "
        f"incidents {body.get('incidents', [])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
