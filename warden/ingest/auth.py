"""Passcode and inject-token checks."""

from __future__ import annotations

from fastapi import Header, HTTPException, Query

from warden.config import settings


def require_inject_token(x_inject_token: str | None = Header(default=None)) -> None:
    expected = settings().inject_token
    if not x_inject_token or x_inject_token != expected:
        raise HTTPException(status_code=401, detail="invalid inject token")


def require_passcode(
    x_passcode: str | None = Header(default=None),
    passcode: str | None = Query(default=None),
) -> None:
    expected = settings().dashboard_passcode
    supplied = x_passcode or passcode
    if supplied != expected:
        raise HTTPException(status_code=401, detail="invalid passcode")
