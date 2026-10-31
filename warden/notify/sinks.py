"""Alert sinks: always log; optionally POST NOTIFY_WEBHOOK_URL."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from warden.config import settings

log = logging.getLogger("warden.notify")


def send_alert(message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    log.warning("ALERT %s %s", message, details or {})
    url = (settings().notify_webhook_url or "").strip()
    if not url.startswith(("http://", "https://")):
        return {"ok": True, "channel": "log"}
    payload = json.dumps({"text": message, "details": details or {}}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        return {"ok": True, "channel": "webhook"}
    except urllib.error.URLError as exc:
        log.warning("notify webhook failed: %s", exc)
        return {"ok": False, "channel": "webhook", "error": str(exc)}
