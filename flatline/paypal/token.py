"""OAuth client-credentials token manager for PayPal sandbox only."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from flatline.config import Settings, settings

log = logging.getLogger("flatline.paypal.token")

TOKEN_PATH = "/v1/oauth2/token"
REFRESH_SKEW_SECONDS = 15 * 60


@dataclass
class Token:
    access_token: str
    expires_at: float
    token_type: str = "Bearer"

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - REFRESH_SKEW_SECONDS


class TokenManager:
    """Cache a sandbox access token; refresh 15 minutes before expiry."""

    def __init__(self, cfg: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._cfg = cfg or settings()
        self._client = client
        self._token: Token | None = None

    @property
    def token_url(self) -> str:
        base = self._cfg.paypal_api_base
        if not base:
            raise RuntimeError("TokenManager only talks to the sandbox host; PAYPAL_ENVIRONMENT=MOCK")
        return f"{base}{TOKEN_PATH}"

    async def get_token(self) -> str:
        if self._token and not self._token.expired:
            return self._token.access_token
        self._token = await self._fetch()
        return self._token.access_token

    async def _fetch(self) -> Token:
        if not self._cfg.paypal_client_id or not self._cfg.paypal_client_secret:
            raise RuntimeError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are required in SANDBOX")
        close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=20)
            close = True
        try:
            resp = await client.post(
                self.token_url,
                data={"grant_type": "client_credentials"},
                auth=(self._cfg.paypal_client_id, self._cfg.paypal_client_secret),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()
        finally:
            if close:
                await client.aclose()
        expires_in = int(body.get("expires_in") or 28800)
        log.info("fetched sandbox access token (expires_in=%ss)", expires_in)
        return Token(
            access_token=str(body["access_token"]),
            expires_at=time.time() + expires_in,
            token_type=str(body.get("token_type") or "Bearer"),
        )
