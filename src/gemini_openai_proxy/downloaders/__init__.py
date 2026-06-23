"""Image download strategies.

Importing this package triggers registration of every built-in
:class:`BaseDownloader` subclass.  The public entry point is
:func:`gemini_openai_proxy.downloaders.chain.generated_image_to_b64`.
"""

from __future__ import annotations

from gemini_openai_proxy.downloaders import (  # noqa: F401 — side-effect imports
    httpx_preview,
    httpx_rpc,
    library_save,
    playwright_preview,
    playwright_rpc,
)
from gemini_openai_proxy.downloaders.base import (
    BaseDownloader,
    all_downloaders,
    register_downloader,
)
from gemini_openai_proxy.downloaders.chain import generated_image_to_b64

__all__ = [
    "BaseDownloader",
    "all_downloaders",
    "generated_image_to_b64",
    "register_downloader",
]
