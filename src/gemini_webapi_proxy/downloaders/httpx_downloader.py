from __future__ import annotations

import httpx

from gemini_webapi_proxy.config import Settings
from gemini_webapi_proxy.downloaders.image_export import (
    _cdn_proxy,
    _download_candidates,
    _download_headers,
)


async def _httpx_get(
    url: str,
    *,
    settings: Settings,
    cookies: dict[str, str],
    referer: str | None = None,
) -> httpx.Response | None:
    headers = _download_headers(referer=referer)
    proxy = _cdn_proxy(settings, url)
    try:
        async with httpx.AsyncClient(
            cookies=cookies,
            proxy=proxy if proxy else None,
            follow_redirects=True,
            timeout=httpx.Timeout(120.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
                ),
            },
        ) as client:
            return await client.get(url, headers=headers)
    except Exception:
        return None


async def fetch_gg_dl_chain_httpx(
    start_url: str,
    *,
    settings: Settings,
    cookies: dict[str, str],
) -> bytes | None:
    """Fallback gg-dl chain via httpx when curl_cffi gets 403 on lh3 hops."""
    url = start_url.strip()
    referer: str | None = "https://gemini.google.com/"
    seen: set[str] = set()

    for _ in range(12):
        if not url or url in seen:
            break
        seen.add(url)

        next_url: str | None = None
        for candidate in _download_candidates(url):
            resp = await _httpx_get(
                candidate,
                settings=settings,
                cookies=cookies,
                referer=referer,
            )
            if resp is None or resp.status_code in {401, 403}:
                continue
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
            if content_type.startswith("image/") and resp.content:
                return resp.content

            text = resp.text.strip()
            if text.startswith("http"):
                next_url = text.split()[0]
                referer = candidate
                break

        if next_url:
            url = next_url
            continue
        break
    return None
