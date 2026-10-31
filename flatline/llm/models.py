"""LiteLLM model resolution from env. Live path only."""

from __future__ import annotations

from typing import Any

from warden.config import Settings, settings


def resolve_model(kind: str, cfg: Settings | None = None) -> str:
    cfg = cfg or settings()
    if kind == "reasoning":
        return cfg.model_reasoning
    return cfg.model_fast


def configure_litellm_env(cfg: Settings | None = None) -> None:
    """Export Azure env vars so LiteLLM can see them (it does not read Settings)."""
    import os

    cfg = cfg or settings()
    if cfg.azure_api_key:
        os.environ.setdefault("AZURE_API_KEY", cfg.azure_api_key)
    if cfg.azure_api_base:
        os.environ.setdefault("AZURE_API_BASE", cfg.azure_api_base)
    if cfg.azure_api_version:
        os.environ.setdefault("AZURE_API_VERSION", cfg.azure_api_version)


def live_complete(model: str, prompt: str, *, json_mode: bool = True) -> str:
    """Call LiteLLM. Never used by tests."""
    configure_litellm_env()
    import litellm

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = litellm.completion(**kwargs)
    return str(resp.choices[0].message.content or "")
