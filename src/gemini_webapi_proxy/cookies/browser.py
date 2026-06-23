"""Read cookies from a desktop browser via ``browser-cookie3``.

Falls back across the installed browsers in the order appropriate for
the host OS (Safari first on macOS, Chrome first everywhere else).
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from gemini_webapi import GeminiClient
from gemini_webapi.constants import AccountStatus
from gemini_webapi.utils.load_browser_cookies import load_browser_cookies

from gemini_webapi_proxy.config import Settings, get_settings
from gemini_webapi_proxy.cookies.base import BaseCookieSource, CookieBundle, register_source
from gemini_webapi_proxy.cookies.session_bootstrap import bootstrap_browser_cookie_session

_BROWSERS_DARWIN = ("safari", "chrome", "edge", "brave", "chromium")
_BROWSERS_OTHER = ("chrome", "edge", "brave", "chromium", "safari")


def _browser_order(preferred: str) -> list[str]:
    base = _BROWSERS_DARWIN if sys.platform == "darwin" else _BROWSERS_OTHER
    if preferred in base:
        return [preferred] + [b for b in base if b != preferred]
    return [preferred, *base]


async def _probe_chat(client: GeminiClient) -> bool:
    try:
        out = await asyncio.wait_for(
            client.generate_content("Reply with exactly: ok", model="gemini-3-flash"),
            timeout=45,
        )
        return bool((out.text or "").strip())
    except Exception:
        return False


async def _load_from_browser_impl(settings: Settings) -> tuple[str, str, dict[str, str]]:
    """The original browser-cookie loader.  Returns ``(psid, psidts, full_map)``.

    Raises :class:`RuntimeError` with a localised message on failure.
    """
    try:
        jars: dict[str, list[dict[str, Any]]] = load_browser_cookies("google.com", verbose=False)
    except Exception as exc:  # browser-cookie3 may be missing on minimal installs
        raise RuntimeError(
            "Could not import browser-cookie3. Install with "
            "`pip install 'gemini-webapi-proxy[browser-cookie]'`."
        ) from exc

    if not jars:
        raise RuntimeError(
            "No browser with Gemini cookies was found. Sign in to "
            "gemini.google.com in Safari or Chrome and try again."
        )

    last_error = ""
    for name in _browser_order(settings.browser):
        if name not in jars:
            continue
        cookie_map = {c["name"]: c["value"] for c in jars[name]}
        psid = cookie_map.get("__Secure-1PSID", "")
        if not psid:
            continue
        psidts = cookie_map.get("__Secure-1PSIDTS", "")
        bootstrap_browser_cookie_session(psid=psid)
        client = GeminiClient(psid, psidts, proxy=settings.http_proxy)
        client.cookies = cookie_map
        try:
            await client.init(timeout=90, auto_refresh=True)
            status = client.account_status
            if status == AccountStatus.AVAILABLE or client.access_token:
                await client.close()
                return psid, psidts, cookie_map
            if await _probe_chat(client):
                await client.close()
                return psid, psidts, cookie_map
            last_error = f"{name}: account_status={status.name}, chat probe failed"
        except Exception as exc:
            last_error = f"{name}: {exc}"
        finally:
            try:
                await client.close()
            except Exception:
                pass

    raise RuntimeError(
        f"Could not find a valid logged-in Gemini cookie. Last error: "
        f"{last_error or 'no browser with __Secure-1PSID found'}"
    )


@register_source
class BrowserCookieSource(BaseCookieSource):
    """Read cookies from the local desktop browser (Safari/Chrome/...)."""

    name = "browser"

    def __init__(self, browser: str | None = None) -> None:
        s = get_settings()
        self._explicit_browser = browser
        # Use a per-instance settings copy when an explicit browser is given
        self._settings = s.model_copy(update={"browser": browser}) if browser else s

    async def load(self) -> CookieBundle:
        psid, psidts, full = await _load_from_browser_impl(self._settings)
        return CookieBundle(psid=psid, psidts=psidts, extras=full)
