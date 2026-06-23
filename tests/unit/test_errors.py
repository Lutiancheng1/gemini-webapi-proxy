"""Unit tests for the error hierarchy and message templates."""

from __future__ import annotations

import pytest

from gemini_openai_proxy.errors import CookieExpiredError, ImageExportError
from gemini_openai_proxy.routes._errors import _looks_like_image_refusal
from gemini_openai_proxy.utils.upstream_refusal import looks_like_upstream_refusal


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
