"""Gateway factory. Agents should wrap the result in ReadOnlyGateway."""

from __future__ import annotations

from flatline.config import Settings, settings
from flatline.paypal.gateway import PayPalGateway, ReadOnlyGateway
from flatline.paypal.mock_gateway import MockGateway
from flatline.paypal.sandbox_gateway import SandboxGateway


def build_gateway(cfg: Settings | None = None) -> PayPalGateway:
    cfg = cfg or settings()
    if cfg.is_mock_paypal:
        return MockGateway()
    return SandboxGateway(cfg)


def build_read_gateway(cfg: Settings | None = None) -> ReadOnlyGateway:
    return ReadOnlyGateway(build_gateway(cfg))
