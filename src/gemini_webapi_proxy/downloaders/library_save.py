"""Library-internal downloader: ask gemini-webapi to save the image itself."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from curl_cffi.requests.exceptions import HTTPError as CurlHTTPError
from curl_cffi.requests.exceptions import RequestException as CurlRequestException
from gemini_webapi.types.image import GeneratedImage

from gemini_webapi_proxy.downloaders.base import BaseDownloader, register_downloader
from gemini_webapi_proxy.downloaders.image_export import (
    _cdn_proxy,
    _is_session_closed_error,
)
from gemini_webapi_proxy.errors import ImageExportError


@register_downloader
class LibrarySaveDownloader(BaseDownloader):
    """Use ``image.save()`` (from gemini-webapi) as a last-resort fallback.

    Tries both full-size and preview variants.
    """

    name = "library-save"
    priority = 90

    async def try_download(
        self,
        image: GeneratedImage,
        *,
        cookies: dict[str, str],
        settings: Any,
        client: Any,
    ) -> bytes | None:
        image.proxy = (
            None if image.url and _cdn_proxy(settings, image.url) is None else settings.http_proxy
        )
        for full_size in (True, False):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    saved = await image.save(
                        path=tmp,
                        filename="out.png",
                        full_size=full_size,
                        client=None,
                    )
                    data = Path(saved).read_bytes()
                    if data:
                        return data
            except CurlHTTPError as exc:
                if exc.response is not None and exc.response.status_code in {401, 403}:
                    return None
                if _is_session_closed_error(exc):
                    raise ImageExportError(str(exc), http_status=503) from exc
            except CurlRequestException as exc:
                if _is_session_closed_error(exc):
                    raise ImageExportError(str(exc), http_status=503) from exc
                continue
            except Exception:
                continue
        return None
