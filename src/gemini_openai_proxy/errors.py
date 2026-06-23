"""Custom exception hierarchy."""

from __future__ import annotations


class ImageExportError(RuntimeError):
    """Failed to materialize Gemini-generated image bytes for OpenAI clients.

    Mapped to HTTP 502 by :func:`gemini_openai_proxy.routes._errors.map_api_error`.
    """

    http_status: int = 502

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class UpstreamRefusalError(RuntimeError):
    """Gemini Web returned a policy / capability refusal instead of a real answer.

    Mapped to HTTP 403 so OpenAI-compatible clients stop immediately instead of
    treating plain-text refusals (e.g. ``I cannot fulfill this request.``) as success.
    """

    http_status = 403

    def __init__(self, message: str) -> None:
        super().__init__(message.strip())


class CookieExpiredError(ImageExportError):
    """Gemini web session cookies are missing, stale, or rejected by Google CDN.

    Mapped to HTTP 401.  Triggers :func:`gemini_openai_proxy.client.pool.invalidate_client`
    so the next request re-reads the cookie source.
    """

    http_status = 401

    @classmethod
    def for_browser_mode(cls) -> CookieExpiredError:
        return cls(
            "Gemini cookies are missing or stale. Sign in to gemini.google.com in "
            "your browser (Safari/Chrome), confirm your local proxy (e.g. 7897) "
            "is reachable, then restart the proxy. When GOP_COOKIE_SOURCE=browser, "
            "the next request will re-read cookies from your browser automatically."
        )

    @classmethod
    def for_env_mode(cls) -> CookieExpiredError:
        return cls(
            "Gemini cookies are missing or stale. Update GOP_GEMINI_1PSID and "
            "GOP_GEMINI_1PSIDTS (or GOP_GEMINI_COOKIES_RAW) and restart the proxy."
        )

    @classmethod
    def for_file_mode(cls) -> CookieExpiredError:
        return cls(
            "Gemini cookies in GOP_COOKIE_FILE are missing or stale. Re-export "
            "your cookies.txt from a browser session logged in to gemini.google.com, "
            "then restart the proxy."
        )
