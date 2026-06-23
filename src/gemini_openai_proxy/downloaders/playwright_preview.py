"""Playwright downloader: use the image.url preview URL as a starting point."""

from __future__ import annotations

from typing import Any

from gemini_openai_proxy.downloaders.base import BaseDownloader, register_downloader


@register_downloader
class PlaywrightPreviewDownloader(BaseDownloader):
    """Walk the gg-dl chain starting from the pre-resolved ``image.url``."""

    name = "playwright-preview"
    priority = 20

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
        from gemini_openai_proxy.downloaders.playwright_downloader import (
            fetch_gg_dl_chain_playwright,
        )

        return await fetch_gg_dl_chain_playwright(start, cookies=cookies, settings=settings)
