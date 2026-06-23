"""Process-wide Gemini client pool.

A single :class:`gemini_webapi.GeminiClient` is lazily initialised on the
first request and re-used thereafter.  The pool is the integration point
between the pluggable :mod:`gemini_webapi_proxy.cookies` sources and the
HTTP layer.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from gemini_webapi import GeminiClient

from gemini_webapi_proxy.client.registry import ModelRegistry
from gemini_webapi_proxy.config import Settings, get_settings
from gemini_webapi_proxy.cookies import build_source
from gemini_webapi_proxy.cookies.session_bootstrap import bootstrap_browser_cookie_session
from gemini_webapi_proxy.downloaders.image_export import sanitize_gemini_client_cookies

_client: GeminiClient | None = None
_lock = asyncio.Lock()
registry = ModelRegistry()


async def _load_cookie_bundle(settings: Settings):
    """Resolve the configured cookie source to a :class:`CookieBundle`."""
    if settings.cookie_source == "browser":
        bootstrap_browser_cookie_session()
        bundle = await build_source("browser", browser=settings.browser).load()
        bootstrap_browser_cookie_session(psid=bundle.psid)
        return bundle
    # env / file: build_source() raises if the source is mis-configured
    return await build_source(settings.cookie_source).load()


async def get_client(settings: Settings | None = None) -> GeminiClient:
    global _client
    settings = settings or get_settings()
    if _client is not None:
        return _client
    async with _lock:
        if _client is not None:
            return _client

        bundle = await _load_cookie_bundle(settings)
        if not bundle.is_valid():
            raise RuntimeError("Cookie source returned an invalid bundle (no __Secure-1PSID)")

        client = GeminiClient(bundle.psid, bundle.psidts, proxy=settings.http_proxy)
        if bundle.extras:
            client.cookies = dict(bundle.extras)
        await client.init(timeout=settings.init_timeout, auto_refresh=True)
        sanitize_gemini_client_cookies(client)

        _client = client
        registry.load_file()
        registry.sync_from_client(client.list_models())
        return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
    from gemini_webapi_proxy.downloaders.playwright_downloader import close_browser_fetch

    await close_browser_fetch()


async def invalidate_client() -> None:
    """Drop cached Gemini client so the next request re-inits (re-reads cookies)."""
    global _client
    async with _lock:
        if _client is not None:
            try:
                await _client.close()
            finally:
                _client = None


@asynccontextmanager
async def lifespan(app):  # type: ignore[no-untyped-def]
    registry.load_file()
    yield
    await close_client()
