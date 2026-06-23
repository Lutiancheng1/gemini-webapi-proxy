"""Unit tests for :mod:`gemini_webapi_proxy.config`."""

from __future__ import annotations

from pathlib import Path

import pytest

from gemini_webapi_proxy.config import (
    REGISTRY_PATH,
    Settings,
    get_settings,
    reset_settings_cache,
)


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOP_PORT", raising=False)
    s = get_settings()
    assert s.port == 4982
    assert s.cookie_source == "env"
    assert s.cdn_direct is True
    assert s.api_key is None  # auth disabled by default


def test_gop_prefix_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOP_PORT", "1234")
    monkeypatch.setenv("GOP_API_KEY", "secret")
    reset_settings_cache()
    s = get_settings()
    assert s.port == 1234
    assert s.api_key == "secret"


def test_legacy_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Old unprefixed env vars (PORT, USE_BROWSER_COOKIES) still work."""
    monkeypatch.setenv("PORT", "7777")
    monkeypatch.setenv("USE_BROWSER_COOKIES", "true")
    # Ensure no explicit GOP_ value overrides.
    monkeypatch.delenv("GOP_PORT", raising=False)
    monkeypatch.delenv("GOP_COOKIE_SOURCE", raising=False)
    reset_settings_cache()
    s = get_settings()
    assert s.port == 7777
    assert s.cookie_source == "browser"


def test_legacy_use_browser_cookies_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USE_BROWSER_COOKIES", "false")
    monkeypatch.delenv("GOP_COOKIE_SOURCE", raising=False)
    reset_settings_cache()
    s = get_settings()
    assert s.cookie_source == "env"


def test_browser_normalisation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOP_BROWSER", "Safari")
    reset_settings_cache()
    s = get_settings()
    assert s.browser == "safari"

    monkeypatch.setenv("GOP_BROWSER", "netscape")  # unknown -> auto
    reset_settings_cache()
    s = get_settings()
    assert s.browser == "auto"


def test_empty_proxy_to_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOP_HTTP_PROXY", "")
    reset_settings_cache()
    s = get_settings()
    assert s.http_proxy is None


def test_registry_path_property(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("GOP_REGISTRY_FILE", "custom.json")
    reset_settings_cache()
    s = get_settings()
    assert s.registry_path == tmp_path / "custom.json"


def test_gemini_cookies_parser() -> None:
    s = Settings(
        port=4982,
        gemini_cookies_raw="__Secure-1PSID=abc; __Secure-1PSIDTS=xyz; NID=ignored",
    )
    parsed = s.gemini_cookies
    assert parsed["__Secure-1PSID"] == "abc"
    assert parsed["__Secure-1PSIDTS"] == "xyz"
    assert "NID" in parsed  # raw parser keeps everything; allow-list is downloader-side


def test_registry_path_default_is_data_dir() -> None:
    """REGISTRY_PATH module constant points at the default data dir."""
    assert REGISTRY_PATH.name == "model_registry.json"
    assert REGISTRY_PATH.parent.name == "data"
