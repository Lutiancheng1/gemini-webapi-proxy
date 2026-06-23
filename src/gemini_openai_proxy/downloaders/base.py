"""Image download strategy abstraction.

A :class:`BaseDownloader` is one strategy for turning a Gemini-generated
:class:`gemini_webapi.GeneratedImage` into raw image bytes.  The proxy
runs them in priority order (lowest first) and uses the first one that
succeeds.

Adding a new strategy:
    1. Subclass :class:`BaseDownloader` and set ``name`` / ``priority``.
    2. Implement :meth:`try_download` to return bytes on success,
       ``None`` to defer to the next strategy, or raise
       :class:`gemini_openai_proxy.errors.ImageExportError` to abort.
    3. The class is auto-registered via the ``@register_downloader``
       decorator and can be enabled in :attr:`Settings.downloader_chain`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseDownloader(ABC):
    """One strategy in the image-download chain."""

    name: ClassVar[str] = "abstract"
    priority: ClassVar[int] = 100  # lower runs first

    def __init__(self, **kwargs: Any) -> None:  # accept arbitrary config
        self._config = kwargs

    @abstractmethod
    async def try_download(
        self,
        image: Any,
        *,
        cookies: dict[str, str],
        settings: Any,
        client: Any,
    ) -> bytes | None:
        """Return image bytes on success, ``None`` to fall through.

        Raise :class:`gemini_openai_proxy.errors.ImageExportError` only
        for non-recoverable errors (e.g. session closed).
        """


_REGISTRY: dict[str, type[BaseDownloader]] = {}


def register_downloader(
    cls: type[BaseDownloader],
) -> type[BaseDownloader]:
    """Class decorator: register a downloader class by ``cls.name``."""
    _REGISTRY[cls.name] = cls
    return cls


def all_downloaders() -> dict[str, type[BaseDownloader]]:
    return dict(_REGISTRY)
