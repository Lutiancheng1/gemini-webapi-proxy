"""httpx-based downloader: use the preview image.url as a starting point."""

from __future__ import annotations

from typing import Any

from gemini_openai_proxy.downloaders.base import BaseDownloader, register_downloader


@register_downloader
class HttpxPreviewDownloader(BaseDownloader):
    """Walk the gg-dl chain over httpx starting from the pre-resolved image.url."""

    name = "httpx-preview"
    priority = 40

    async def try_download(
        self,
        image: Any,
        *,
        cookies: dict[str, str],
        settings: Any,
        client: Any,
    ) -> bytes | None:
        start = getattr(image, "url", None)
        if not start:
            return None
        from gemini_openai_proxy.downloaders.httpx_downloader import (
            fetch_gg_dl_chain_httpx,
        )

        return await fetch_gg_dl_chain_httpx(start, settings=settings, cookies=cookies)
