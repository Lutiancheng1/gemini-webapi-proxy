"""httpx-based downloader: take the RPC URL and walk the chain."""

from __future__ import annotations

from typing import Any

from gemini_webapi_proxy.downloaders.base import BaseDownloader, register_downloader
from gemini_webapi_proxy.downloaders.image_export import _resolve_rpc_start


@register_downloader
class HttpxRPCDownloader(BaseDownloader):
    """Walk the gg-dl chain over httpx. Used as a fallback when Playwright fails."""

    name = "httpx-rpc"
    priority = 30

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
        from gemini_webapi_proxy.downloaders.httpx_downloader import (
            fetch_gg_dl_chain_httpx,
        )

        return await fetch_gg_dl_chain_httpx(start, settings=settings, cookies=cookies)
