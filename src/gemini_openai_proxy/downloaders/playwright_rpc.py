"""Playwright-Chromium downloader: take the RPC full-size URL and walk the chain."""

from __future__ import annotations

import logging
from typing import Any

from gemini_openai_proxy.downloaders.base import BaseDownloader, register_downloader
from gemini_openai_proxy.downloaders.image_export import _resolve_rpc_start

logger = logging.getLogger(__name__)


@register_downloader
class PlaywrightRPCDownloader(BaseDownloader):
    """Use the RPC full-size URL through Playwright's request context.

    This is the most reliable strategy on the gg-dl/lh3 redirect chain
    because Chromium's TLS fingerprint matches what Google expects.
    """

    name = "playwright-rpc"
    priority = 10

    async def try_download(
        self,
        image: Any,
        *,
        cookies: dict[str, str],
        settings: Any,
        client: Any,
    ) -> bytes | None:
        start = await _resolve_rpc_start(image, client)
        if not start:
            return None
        from gemini_openai_proxy.downloaders.playwright_downloader import (
            fetch_gg_dl_chain_playwright,
        )

        return await fetch_gg_dl_chain_playwright(start, cookies=cookies, settings=settings)
