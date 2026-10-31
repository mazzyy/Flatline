#!/usr/bin/env python3
"""Replay stored events into a fresh detector scan (in-process)."""

from __future__ import annotations

from flatline.config import apply_sandbox_guard
from flatline.db.session import create_schema, get_sessionmaker
from flatline.detector.worker import scan_once


def main() -> None:
    apply_sandbox_guard()
    create_schema()
    db = get_sessionmaker()()
    try:
        incidents = scan_once(db)
        db.commit()
        print(f"scan produced {len(incidents)} incident row(s)")
        for inc in incidents:
            print(f"  {inc.playbook} {inc.status} observed={inc.observed_value}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
