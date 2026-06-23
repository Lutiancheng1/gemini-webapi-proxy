"""Application configuration (pydantic-settings v2).

All settings are read from environment variables (and a ``.env`` file at the
project root, if present). Variables are prefixed with ``GOP_``; a few
well-known unprefixed names (``PORT``, ``HTTP_PROXY``) are also accepted for
convenience but should be migrated to the prefixed form over time.

The :func:`get_settings` function is a process-wide cached accessor; tests
can call :func:`reset_settings_cache` between cases.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gemini_openai_proxy.utils.cookies import parse_cookie_string

# ---- Project paths --------------------------------------------------------
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_REGISTRY_FILE = "model_registry.json"

# Backwards-compat module-level constant.  This is a *snapshot* of the
# default value; if the user changes ``GOP_DATA_DIR`` at runtime, code
# should read :func:`get_settings().registry_path` instead.
REGISTRY_PATH: Path = DEFAULT_DATA_DIR / DEFAULT_REGISTRY_FILE

# Load .env from the project root if it exists.  We do NOT pollute the host
# environment — explicit env vars always win.
load_dotenv(PROJECT_ROOT / ".env", override=False)


# ---- The pydantic-settings model -----------------------------------------
class Settings(BaseSettings):
    """Strongly-typed configuration. See ``docs/configuration.md`` for details."""

    model_config = SettingsConfigDict(
        env_prefix="GOP_",
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # -- Server -----------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 4982
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "console"
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # -- Auth -------------------------------------------------------------
    # When api_key is set (non-empty), Authorization: Bearer <api_key> is
    # required.  When empty (default), authentication is bypassed for
    # backward compatibility with local single-user setups.
    api_key: str | None = None

    # -- Cookie source ----------------------------------------------------
    cookie_source: Literal["browser", "env", "file"] = "browser"
    browser: str = "auto"  # auto / safari / chrome / edge / brave / chromium
    cookie_file: Path | None = None  # Netscape-format cookie file
    gemini_1psid: str | None = None
    gemini_1psidts: str | None = None
    gemini_cookies_raw: str = ""  # "k1=v1; k2=v2" form

    # -- Network ----------------------------------------------------------
    http_proxy: str | None = None
    cdn_direct: bool = True  # bypass proxy for Google CDN domains

    # -- Behaviour --------------------------------------------------------
    chat_timeout: float = 180.0
    image_timeout: float = 300.0
    init_timeout: float = 120.0
    probe_on_start: bool = False
    probe_models: bool = True
    enable_stream: bool = False  # not implemented yet; see roadmap

    # -- Data -------------------------------------------------------------
    data_dir: Path = DEFAULT_DATA_DIR
    registry_file: str = DEFAULT_REGISTRY_FILE

    # -- Downloader chain -------------------------------------------------
    downloader_chain: list[str] = Field(
        default_factory=lambda: [
            "playwright-rpc",
            "playwright-preview",
            "httpx-rpc",
            "httpx-preview",
            "library-rpc",
            "library-save",
        ]
    )
    downloader_timeout: float = 120.0

    # ------------------------------------------------------------------ API
    @property
    def registry_path(self) -> Path:
        return self.data_dir / self.registry_file

    @property
    def gemini_cookies(self) -> dict[str, str]:
        return parse_cookie_string(self.gemini_cookies_raw) if self.gemini_cookies_raw else {}

    @field_validator("browser")
    @classmethod
    def _normalize_browser(cls, v: str) -> str:
        v = v.strip().lower()
        if v == "auto":
            return v
        allowed = {"safari", "chrome", "edge", "brave", "chromium", "firefox"}
        if v not in allowed:
            # Don't crash — fall back to "auto"; a downstream warning will fire.
            return "auto"
        return v

    @field_validator("http_proxy", mode="before")
    @classmethod
    def _empty_string_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("api_key", mode="before")
    @classmethod
    def _empty_api_key_to_none(cls, v: Any) -> Any:
        if isinstance(v, str) and not v.strip():
            return None
        return v


# ---- Backward-compat shim for unprefixed env vars -------------------------
# We honour the historical names so existing `.env` files keep working.
# New code should always set the `GOP_`-prefixed form.
_LEGACY_ALIASES: dict[str, str] = {
    "PORT": "GOP_PORT",
    "HOST": "GOP_HOST",
    "HTTP_PROXY": "GOP_HTTP_PROXY",
    "HTTPS_PROXY": "GOP_HTTP_PROXY",
    "USE_BROWSER_COOKIES": "GOP_COOKIE_SOURCE",  # special: see _apply_legacy
    "BROWSER_COOKIE": "GOP_BROWSER",
    "GEMINI_1PSID": "GOP_GEMINI_1PSID",
    "GEMINI_1PSIDTS": "GOP_GEMINI_1PSIDTS",
    "GEMINI_COOKIES": "GOP_GEMINI_COOKIES_RAW",
    "PROBE_ON_START": "GOP_PROBE_ON_START",
    "PROBE_MODELS": "GOP_PROBE_MODELS",
}


def _apply_legacy_env() -> None:
    """Copy well-known unprefixed vars to their ``GOP_`` equivalents."""
    for legacy, new in _LEGACY_ALIASES.items():
        legacy_val = os.environ.get(legacy)
        if legacy_val is None:
            continue
        new_val = os.environ.get(new)
        # Don't override an explicit GOP_ value.
        if new_val is not None:
            continue
        if legacy == "USE_BROWSER_COOKIES":
            # Translate: true -> "browser", false -> "env"
            os.environ[new] = "browser" if legacy_val.lower() in {"1", "true", "yes"} else "env"
        else:
            os.environ[new] = legacy_val


# ---- Cached accessor ------------------------------------------------------
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _apply_legacy_env()
    return Settings()  # type: ignore[call-arg]


def reset_settings_cache() -> None:
    """Clear the cached :func:`get_settings` result. Used in tests."""
    get_settings.cache_clear()
