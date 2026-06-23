"""Unit tests for the cookie-source registry and individual sources."""

from __future__ import annotations

import pytest

from gemini_webapi_proxy.cookies import (
    SOURCES,
    CookieBundle,
    build_source,
)


def test_sources_registered() -> None:
    assert {"browser", "env", "file"}.issubset(SOURCES.keys())


def test_build_source_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown cookie source"):
        build_source("nope")


def test_env_source_requires_psid(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_webapi_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_COOKIE_SOURCE", "env")
    monkeypatch.delenv("GOP_GEMINI_1PSID", raising=False)
    reset_settings_cache()

    import asyncio

    from gemini_webapi_proxy.cookies import build_source as bs

    with pytest.raises(RuntimeError, match="GOP_GEMINI_1PSID"):
        asyncio.run(bs("env").load())


def test_env_source_loads(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_webapi_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_COOKIE_SOURCE", "env")
    monkeypatch.setenv("GOP_GEMINI_1PSID", "psid123")
    monkeypatch.setenv("GOP_GEMINI_1PSIDTS", "psidts456")
    reset_settings_cache()

    import asyncio

    from gemini_webapi_proxy.cookies import build_source as bs

    bundle = asyncio.run(bs("env").load())
    assert bundle.psid == "psid123"
    assert bundle.psidts == "psidts456"
    assert bundle.is_valid()


def test_file_source_loads_netscape(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_webapi_proxy.config import reset_settings_cache

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(
        "# Netscape HTTP Cookie File\n"
        ".google.com\tTRUE\t/\tTRUE\t9999999999\t__Secure-1PSID\tabc123\n"
        ".google.com\tTRUE\t/\tTRUE\t9999999999\t__Secure-1PSIDTS\txyz789\n"
        "HttpOnly_.google.com\tTRUE\t/\tFALSE\t9999999999\tSIDCC\thi\n"
    )
    monkeypatch.setenv("GOP_COOKIE_FILE", str(cookie_file))
    reset_settings_cache()

    import asyncio

    from gemini_webapi_proxy.cookies import build_source as bs

    bundle = asyncio.run(bs("file").load())
    assert bundle.psid == "abc123"
    assert bundle.psidts == "xyz789"
    assert bundle.extras["SIDCC"] == "hi"


def test_file_source_requires_psid(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_webapi_proxy.config import reset_settings_cache

    cookie_file = tmp_path / "cookies.txt"
    cookie_file.write_text(".google.com\tTRUE\t/\tTRUE\t0\tfoo\tbar\n")
    monkeypatch.setenv("GOP_COOKIE_FILE", str(cookie_file))
    reset_settings_cache()

    import asyncio

    from gemini_webapi_proxy.cookies import build_source as bs

    with pytest.raises(RuntimeError, match="__Secure-1PSID"):
        asyncio.run(bs("file").load())


def test_bundle_is_valid() -> None:
    assert CookieBundle(psid="x", psidts="y").is_valid()
    assert not CookieBundle(psid="", psidts="y").is_valid()
