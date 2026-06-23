"""Download-chain orchestrator + public ``generated_image_to_b64`` entry point.

The orchestrator walks the configured list of :class:`BaseDownloader`
strategies in priority order and returns the first non-empty result.  Each
strategy may log its own failure; the final fallback raises an
:class:`ImageExportError` summarising every attempt.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from gemini_webapi.exceptions import AuthError

from gemini_openai_proxy.config import Settings
from gemini_openai_proxy.downloaders import image_export as _compat
from gemini_openai_proxy.downloaders.base import (
    BaseDownloader,
    all_downloaders,
)
from gemini_openai_proxy.errors import (
    CookieExpiredError,
    ImageExportError,
)

logger = logging.getLogger(__name__)


def _build_chain(settings: Settings) -> list[BaseDownloader]:
    """Instantiate the configured downloader chain, preserving order."""
    available = all_downloaders()
    chain: list[BaseDownloader] = []
    for name in settings.downloader_chain:
        cls = available.get(name)
        if cls is None:
            logger.warning("Unknown downloader in chain: %s — skipping", name)
            continue
        chain.append(cls())
    if not chain:
        raise RuntimeError(
            f"No downloaders could be loaded from chain {settings.downloader_chain!r}. "
            f"Available: {sorted(available)}"
        )
    # Sort by declared priority in case the user provided an unsorted list.
    chain.sort(key=lambda d: d.priority)
    return chain


def _cookie_error(settings: Settings) -> CookieExpiredError:
    if settings.cookie_source == "browser":
        return CookieExpiredError.for_browser_mode()
    if settings.cookie_source == "file":
        return CookieExpiredError.for_file_mode()
    return CookieExpiredError.for_env_mode()


async def _run_chain(
    image: Any,
    *,
    settings: Settings,
    client: Any,
    cookies: dict[str, str],
) -> bytes:
    """Walk the chain, collecting per-strategy failure reasons."""
    attempts: list[str] = []
    for downloader in _build_chain(settings):
        try:
            data = await downloader.try_download(
                image, cookies=cookies, settings=settings, client=client
            )
            if data:
                return data
            attempts.append(f"{downloader.name}: no bytes")
        except CookieExpiredError:
            raise
        except ImageExportError as exc:
            if exc.http_status == 503:
                raise
            attempts.append(f"{downloader.name}: {exc}")
        except Exception as exc:
            attempts.append(f"{downloader.name}: {exc}")
    detail = "; ".join(attempts[-8:]) if attempts else "no downloaders ran"
    raise ImageExportError(
        f"Unable to download Gemini-generated image bytes ({detail}). "
        "Downstream clients should not fetch lh3.googleusercontent.com/gg-dl "
        "links directly.",
        http_status=502,
    )


async def generated_image_to_b64(
    image: Any,
    *,
    settings: Settings,
    client: Any,
) -> str:
    """Public entry point: download an image and return base64-encoded bytes.

    Performs up to 3 passes:
      * on ``AuthError`` / 401-403: invalidate the client and re-read
        cookies from the configured source
      * on ``ImageExportError(503)``: re-init the underlying session
      * on other ``ImageExportError``: re-init and try again
    """
    last_cookie_err: CookieExpiredError | None = None
    last_exc: Exception | None = None

    for pass_idx in range(3):
        try:
            cookies = _compat.sanitize_gemini_client_cookies(client)
            data = await _run_chain(image, settings=settings, client=client, cookies=cookies)
            return base64.b64encode(data).decode()
        except AuthError as exc:
            last_cookie_err = _cookie_error(settings)
            last_cookie_err.__cause__ = exc
            last_exc = exc
        except CookieExpiredError as exc:
            last_cookie_err = exc
            last_exc = exc
        except ImageExportError as exc:
            last_exc = exc
            if pass_idx < 2:
                continue
            raise
        except Exception as exc:
            last_exc = ImageExportError(f"Download failed: {exc}", http_status=502)
            if pass_idx < 2:
                continue
            raise last_exc from exc

        # Cookie-error path: invalidate and re-read the configured source
        if pass_idx < 2 and last_cookie_err is not None and settings.cookie_source == "browser":
            from gemini_openai_proxy.client.pool import (
                get_client,
                invalidate_client,
            )

            await invalidate_client()
            client = await get_client(settings)
            continue
        break

    if last_cookie_err is not None:
        raise _cookie_error(settings) from last_cookie_err
    if last_exc is not None:
        raise last_exc
    raise _cookie_error(settings)
