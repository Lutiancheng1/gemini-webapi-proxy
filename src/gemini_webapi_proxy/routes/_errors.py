"""Shared error helpers used by the route modules."""

from __future__ import annotations

import asyncio

from fastapi.responses import JSONResponse
from gemini_webapi.exceptions import AuthError

from gemini_webapi_proxy.client.pool import invalidate_client
from gemini_webapi_proxy.config import Settings
from gemini_webapi_proxy.errors import CookieExpiredError, ImageExportError, UpstreamRefusalError
from gemini_webapi_proxy.schemas import ErrorResponse
from gemini_webapi_proxy.utils.upstream_refusal import (
    COOKIE_REAUTH_HINT,
    looks_like_image_refusal,
    looks_like_upstream_refusal,
)

# Re-export for tests
_looks_like_image_refusal = looks_like_image_refusal
_looks_like_chat_refusal = looks_like_upstream_refusal


def error_json(message: str, status: int = 500) -> JSONResponse:
    """Build the standard ``{error: {message, type}}`` JSON response."""
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(error={"message": message, "type": "api_error"}).model_dump(),
    )


def _with_reauth_hint(text: str) -> str:
    """Append the re-authentication guidance to an upstream-refusal message."""
    if COOKIE_REAUTH_HINT in text:
        return text
    return f"{text}  --  {COOKIE_REAUTH_HINT}"


async def map_api_error(exc: Exception, settings: Settings) -> JSONResponse:
    """Map an internal exception to the public OpenAI-style error response."""
    if isinstance(exc, CookieExpiredError):
        await invalidate_client()
        return error_json(str(exc), exc.http_status)
    if isinstance(exc, ImageExportError):
        return error_json(str(exc), exc.http_status)
    if isinstance(exc, UpstreamRefusalError):
        return error_json(
            _with_reauth_hint(f"Upstream refused request: {exc}"),
            exc.http_status,
        )
    if isinstance(exc, AuthError):
        await invalidate_client()
        if settings.cookie_source == "browser":
            msg: CookieExpiredError = CookieExpiredError.for_browser_mode()
        elif settings.cookie_source == "file":
            msg = CookieExpiredError.for_file_mode()
        else:
            msg = CookieExpiredError.for_env_mode()
        return error_json(str(msg), 401)
    if isinstance(exc, asyncio.TimeoutError):
        return error_json("Request timed out", 504)
    if isinstance(exc, RuntimeError):
        text = str(exc)
        if looks_like_image_refusal(text) or looks_like_upstream_refusal(text):
            return error_json(
                _with_reauth_hint(f"Upstream refused request: {text}"),
                status=403,
            )
        return error_json(text, 500)
    return error_json(str(exc))
