"""Unit tests for the error hierarchy and message templates."""

from __future__ import annotations

import pytest

from gemini_webapi_proxy.config import Settings, reset_settings_cache
from gemini_webapi_proxy.errors import CookieExpiredError, ImageExportError
from gemini_webapi_proxy.routes._errors import _looks_like_image_refusal, map_api_error
from gemini_webapi_proxy.utils.upstream_refusal import (
    COOKIE_REAUTH_HINT,
    looks_like_upstream_refusal,
)


def test_image_export_error_default_status() -> None:
    e = ImageExportError("boom")
    assert e.http_status == 502
    assert str(e) == "boom"


def test_image_export_error_custom_status() -> None:
    e = ImageExportError("boom", http_status=503)
    assert e.http_status == 503


def test_cookie_expired_browser_message() -> None:
    msg = str(CookieExpiredError.for_browser_mode())
    assert "browser" in msg.lower()
    assert "gemini.google.com" in msg
    assert CookieExpiredError.for_browser_mode().http_status == 401


def test_cookie_expired_env_message() -> None:
    msg = str(CookieExpiredError.for_env_mode())
    assert "GOP_GEMINI_1PSID" in msg
    assert CookieExpiredError.for_env_mode().http_status == 401


def test_cookie_expired_file_message() -> None:
    msg = str(CookieExpiredError.for_file_mode())
    assert "GOP_COOKIE_FILE" in msg


@pytest.mark.parametrize(
    "text",
    [
        "I can try to find an image like that for you, but can't create it right now.",
        "Are you signed in? I can search for images, but can't seem to create any for you right now.",
        "Image generation isn't available in your location yet.",
        "Feature isn't available for your account.",
        "Something went wrong, try again later.",
        # New variant seen 2026-06 after Safari re-login: Gemini sometimes
        # responds with a generic "I don't have access" instead of the
        # classic "image creation isn't available" phrasing.
        "Normally I can help with things like this, but I don't seem to have access to that content.",
        "I'm not able to create that image right now.",
    ],
)
def test_image_refusal_detection(text: str) -> None:
    assert _looks_like_image_refusal(text)


@pytest.mark.parametrize(
    "text",
    [
        "OK",
        "PONG",
        "Here's a recipe for apple pie: ...",
        "The capital of France is Paris.",
    ],
)
def test_non_refusal_text_not_detected(text: str) -> None:
    assert not _looks_like_image_refusal(text)


@pytest.mark.parametrize(
    "text",
    [
        "I cannot fulfill this request.",
        "I'm unable to help with that request.",
    ],
)
def test_chat_refusal_detection(text: str) -> None:
    assert looks_like_upstream_refusal(text)


def test_reauth_hint_present() -> None:
    """The re-auth guidance string is non-empty and points at Safari + sync."""
    assert "gemini.google.com" in COOKIE_REAUTH_HINT
    assert "sync" in COOKIE_REAUTH_HINT.lower()


def test_refusal_response_includes_reauth_hint() -> None:
    """map_api_error must append the re-auth guidance to 403 responses."""
    import asyncio

    reset_settings_cache()
    s = Settings()
    resp = asyncio.run(
        map_api_error(
            RuntimeError(
                "Normally I can help with things like this, but I don't seem to have access to that content."
            ),
            s,
        )
    )
    assert resp.status_code == 403
    import json as _json

    body = _json.loads(resp.body)
    assert "Safari" in body["error"]["message"]
    assert "sync" in body["error"]["message"].lower()
