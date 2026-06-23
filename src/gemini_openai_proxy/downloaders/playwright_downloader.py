from __future__ import annotations

import asyncio
from typing import Any

from gemini_openai_proxy.config import Settings

_GG_DL_MARKERS = ("gg-dl", "googleusercontent.com", "usercontent.google.com")
_GEMINI_HEADERS = {
    "Referer": "https://gemini.google.com/",
    "Origin": "https://gemini.google.com",
}
_MAX_HOPS = 12

_playwright: Any = None
_browser: Any = None
_context: Any = None
_warmed = False
_cookie_fingerprint: str | None = None
_lock = asyncio.Lock()


def _is_gg_dl_url(url: str) -> bool:
    lower = url.lower()
    return any(marker in lower for marker in _GG_DL_MARKERS)


def _download_candidates(url: str) -> list[str]:
    cleaned = url.strip()
    if not cleaned:
        return []
    out = [cleaned]
    if _is_gg_dl_url(cleaned) and "=d-I" not in cleaned:
        out.append(f"{cleaned}=d-I?alr=yes")
    return out


def _load_playwright_cookies(
    cookies: dict[str, str],
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    if settings is not None and settings.use_browser_cookies:
        try:
            import browser_cookie3

            loader = getattr(browser_cookie3, settings.browser_name, browser_cookie3.safari)
            raw = list(loader(domain_name="google.com"))
            out: list[dict[str, Any]] = []
            for ck in raw:
                if ck.name.startswith("__Host-"):
                    continue
                dom = ck.domain or ".google.com"
                if not dom.startswith("."):
                    dom = "." + dom.lstrip(".")
                out.append(
                    {
                        "name": ck.name,
                        "value": ck.value,
                        "domain": dom,
                        "path": ck.path or "/",
                        "expires": -1,
                        "httpOnly": False,
                        "secure": True,
                        "sameSite": "Lax",
                    }
                )
            if out:
                return out
        except Exception:
            pass

    out = []
    for name, value in cookies.items():
        if not value or name.startswith("__Host-"):
            continue
        out.append(
            {
                "name": name,
                "value": value,
                "domain": ".google.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "Lax",
            }
        )
    return out


async def _ensure_context(
    cookies: dict[str, str],
    settings: Settings | None = None,
) -> Any:
    global _playwright, _browser, _context, _warmed, _cookie_fingerprint
    from playwright.async_api import async_playwright

    pw_cookies = _load_playwright_cookies(cookies, settings)
    fp = repr([(c["name"], c["domain"], c["value"]) for c in pw_cookies])
    async with _lock:
        if _context is not None and _warmed and _cookie_fingerprint == fp:
            return _context

        if _playwright is None:
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(headless=True)

        if _context is not None:
            await _context.close()
            _context = None
            _warmed = False

        _context = await _browser.new_context()
        if pw_cookies:
            await _context.add_cookies(pw_cookies)

        page = await _context.new_page()
        await page.goto(
            "https://gemini.google.com/",
            wait_until="domcontentloaded",
            timeout=90_000,
        )
        await page.close()
        _warmed = True
        _cookie_fingerprint = fp
        return _context


async def close_browser_fetch() -> None:
    global _playwright, _browser, _context, _warmed, _cookie_fingerprint
    async with _lock:
        if _context is not None:
            await _context.close()
            _context = None
        if _browser is not None:
            await _browser.close()
            _browser = None
        if _playwright is not None:
            await _playwright.stop()
            _playwright = None
        _warmed = False
        _cookie_fingerprint = None


async def fetch_gg_dl_chain_playwright(
    start_url: str,
    *,
    cookies: dict[str, str],
    settings: Settings | None = None,
) -> bytes | None:
    """
    Download gg-dl / rd-gg-dl bytes via headless Chromium request context.

    Chromium TLS + cookie jar succeeds on lh3 hop-3 where curl_cffi gets 403.
    CDN redirect URLs are short-lived — call this immediately after generation.
    """
    url = start_url.strip()
    if not url:
        return None

    ctx = await _ensure_context(cookies, settings)
    api = ctx.request
    referer = dict(_GEMINI_HEADERS)
    seen: set[str] = set()

    for _ in range(_MAX_HOPS):
        if url in seen:
            break
        seen.add(url)

        next_url: str | None = None
        for candidate in _download_candidates(url):
            try:
                resp = await api.get(candidate, headers=referer, timeout=120_000)
            except Exception:
                continue

            if resp.status in {401, 403}:
                continue
            if resp.status != 200:
                continue

            content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
            body = await resp.body()
            if content_type.startswith("image/") and body:
                return body

            text = body.decode("utf-8", "replace").strip()
            if text.startswith("http"):
                next_url = text.split()[0]
                break

        if next_url:
            url = next_url
            continue
        break

    return None
