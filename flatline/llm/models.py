"""LiteLLM model resolution from env. Live path only."""

from __future__ import annotations

from typing import Any

from flatline.config import Settings, settings


def resolve_model(kind: str, cfg: Settings | None = None) -> str:
    cfg = cfg or settings()
    if kind == "reasoning":
        return cfg.model_reasoning
    return cfg.model_fast


def configure_litellm_env(cfg: Settings | None = None) -> None:
    """Export provider env vars so LiteLLM can see them (it does not read Settings).

    Any LiteLLM provider works through MODEL_FAST / MODEL_REASONING, for example
    azure/<deployment>, gemini/<model> or ollama_chat/<model>.
    """
    import os

    cfg = cfg or settings()
    exported = {
        "AZURE_API_KEY": cfg.azure_api_key,
        "AZURE_API_BASE": cfg.azure_api_base,
        "AZURE_API_VERSION": cfg.azure_api_version,
        "GEMINI_API_KEY": cfg.gemini_api_key,
        "OLLAMA_API_BASE": cfg.ollama_api_base,
    }
    for key, value in exported.items():
        if value:
            os.environ.setdefault(key, value)


def live_complete(model: str, prompt: str, *, json_mode: bool = True) -> str:
    """Call LiteLLM. Never used by tests."""
    configure_litellm_env()
    import litellm

    litellm.suppress_debug_info = True  # no "Give Feedback" banner on every error
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": 90,
        "num_retries": 2,  # free tiers answer 429 now and then
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = litellm.completion(**kwargs)
    return str(resp.choices[0].message.content or "")
