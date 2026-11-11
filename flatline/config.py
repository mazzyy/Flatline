"""Environment loading and the sandbox guard.

Every process imports this before talking to PayPal. Any value of
``PAYPAL_ENVIRONMENT`` other than ``MOCK`` or ``SANDBOX`` refuses to start.
There is no code path to live PayPal endpoints.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("flatline.config")

PayPalEnvironment = Literal["MOCK", "SANDBOX"]
LlmMode = Literal["mock", "live"]


class SandboxGuardError(RuntimeError):
    """Raised when PAYPAL_ENVIRONMENT is anything other than MOCK or SANDBOX."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    paypal_environment: str = Field(default="MOCK", alias="PAYPAL_ENVIRONMENT")
    llm_mode: str = Field(default="mock", alias="LLM_MODE")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    verify_minutes: int = Field(default=10, alias="VERIFY_MINUTES")
    demo_mode: bool = Field(default=False, alias="DEMO_MODE")
    # Run the detector and agent loops inside the API process (one free Render service).
    run_workers: bool = Field(default=False, alias="RUN_WORKERS")

    paypal_client_id: str = Field(default="", alias="PAYPAL_CLIENT_ID")
    paypal_client_secret: str = Field(default="", alias="PAYPAL_CLIENT_SECRET")
    paypal_webhook_id: str = Field(default="", alias="PAYPAL_WEBHOOK_ID")
    paypal_sandbox_plan_id: str = Field(default="", alias="PAYPAL_SANDBOX_PLAN_ID")
    paypal_sandbox_product_id: str = Field(default="", alias="PAYPAL_SANDBOX_PRODUCT_ID")

    model_fast: str = Field(default="gemini/gemini-2.5-flash-lite", alias="MODEL_FAST")
    model_reasoning: str = Field(default="gemini/gemini-2.5-flash", alias="MODEL_REASONING")
    # Comma separated. Tried in order when the agent's own model fails (a free tier 429).
    model_fallbacks: str = Field(default="", alias="MODEL_FALLBACKS")
    azure_api_key: str = Field(default="", alias="AZURE_API_KEY")
    azure_api_base: str = Field(default="", alias="AZURE_API_BASE")
    azure_api_version: str = Field(default="2024-08-01-preview", alias="AZURE_API_VERSION")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ollama_api_base: str = Field(default="", alias="OLLAMA_API_BASE")

    database_url: str = Field(
        default="postgresql+psycopg://flatline:flatline@localhost:5432/flatline",
        alias="DATABASE_URL",
    )

    refund_approval_max: float = Field(default=50.00, alias="REFUND_APPROVAL_MAX")
    # A refund at or under this runs without a click. 0 (the default): every refund waits.
    auto_refund_max: float = Field(default=0.00, alias="AUTO_REFUND_MAX")
    # The most the agents may refund in any 24 hours, approved or automatic.
    daily_refund_budget: float = Field(default=200.00, alias="DAILY_REFUND_BUDGET")
    auto_actions_enabled: bool = Field(default=True, alias="AUTO_ACTIONS_ENABLED")

    # Recovery: after an incident is resolved, ask the lost sales back (always with approval).
    recovery_enabled: bool = Field(default=True, alias="RECOVERY_ENABLED")
    recovery_max_links: int = Field(default=25, alias="RECOVERY_MAX_LINKS")
    recovery_max_total: float = Field(default=1000.00, alias="RECOVERY_MAX_TOTAL")

    dashboard_passcode: str = Field(default="demo-judge", alias="DASHBOARD_PASSCODE")
    inject_token: str = Field(default="change-me", alias="INJECT_TOKEN")

    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_repo: str = Field(default="mazzyy/Flatline", alias="GITHUB_REPO")
    notify_webhook_url: str = Field(default="", alias="NOTIFY_WEBHOOK_URL")
    flatline_api_url: str = Field(default="http://localhost:8000", alias="FLATLINE_API_URL")
    shop_port: int = Field(default=3000, alias="SHOP_PORT")
    # Where a browser finds the demo shop. Empty: the same host on port 3000 (local setup).
    shop_public_url: str = Field(default="", alias="SHOP_PUBLIC_URL")
    # One-container hosting: the API serves the shop under /shop by passing requests on
    # to the shop process at this address (scripts/start.sh sets both values).
    shop_internal_url: str = Field(default="", alias="SHOP_INTERNAL_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("paypal_environment")
    @classmethod
    def _normalize_paypal_env(cls, value: str) -> str:
        return (value or "").strip().upper()

    @field_validator("llm_mode")
    @classmethod
    def _normalize_llm_mode(cls, value: str) -> str:
        return (value or "").strip().lower()

    @model_validator(mode="after")
    def _sandbox_guard(self) -> Settings:
        if self.paypal_environment not in ("MOCK", "SANDBOX"):
            raise SandboxGuardError(
                f"PAYPAL_ENVIRONMENT={self.paypal_environment!r} is not allowed. "
                "Set PAYPAL_ENVIRONMENT=MOCK or PAYPAL_ENVIRONMENT=SANDBOX. "
                "Live PayPal is impossible to enable: there is no code path to it."
            )
        if self.llm_mode not in ("mock", "live"):
            raise ValueError(f"LLM_MODE={self.llm_mode!r} is not allowed. Use 'mock' or 'live'.")
        return self

    @property
    def is_mock_paypal(self) -> bool:
        return self.paypal_environment == "MOCK"

    @property
    def is_mock_llm(self) -> bool:
        return self.llm_mode == "mock"

    @property
    def paypal_api_base(self) -> str:
        """Sandbox REST host only. Live host is never returned."""
        if self.paypal_environment != "SANDBOX":
            return ""
        return "https://api-m.sandbox.paypal.com"

    @property
    def effective_verify_minutes(self) -> int:
        if self.demo_mode:
            return min(self.verify_minutes, 1)
        return self.verify_minutes


@lru_cache
def settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    """Drop the cached Settings instance. Used by tests."""
    settings.cache_clear()


def apply_sandbox_guard() -> Settings:
    """Load settings and fail loudly if the environment is not MOCK/SANDBOX."""
    return settings()
