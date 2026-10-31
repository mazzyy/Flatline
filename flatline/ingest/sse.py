"""In-process SSE hub. Every subscriber gets every event after they connect."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _json(value: Any) -> Any:
    if hasattr(value, "hex"):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class Hub:
    def __init__(self) -> None:
        self._subs: list[asyncio.Queue[dict[str, Any]]] = []

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subs.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[dict[str, Any]]) -> None:
        if q in self._subs:
            self._subs.remove(q)

    def publish(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "event": event,
            "at": datetime.now(UTC).isoformat(),
            "data": {k: _json(v) for k, v in data.items()},
        }
        for q in list(self._subs):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(payload)
        return payload

    async def stream(self) -> AsyncIterator[str]:
        q = self.subscribe()
        try:
            yield _format({"event": "ready", "data": {"ok": True}, "id": "0", "at": ""})
            while True:
                item = await q.get()
                yield _format(item)
        finally:
            self.unsubscribe(q)


def _format(item: dict[str, Any]) -> str:
    return f"event: {item['event']}\nid: {item['id']}\ndata: {json.dumps(item)}\n\n"


HUB = Hub()
