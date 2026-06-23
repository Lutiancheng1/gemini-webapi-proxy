"""Abstract Gemini client.

The proxy currently wraps :class:`gemini_webapi.GeminiClient` (reverse-
engineered client of the Gemini Web frontend).  This module defines a
narrow interface that other backends (e.g. an unofficial REST adapter, a
mock for tests) can implement in the future without touching the rest of
the codebase.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ModelDescriptor:
    """One model entry returned by ``list_models()``."""

    name: str
    display_name: str = ""
    description: str = ""
    is_available: bool = True

    # ``model_name`` is the legacy name used by the gemini-webapi client and
    # the on-disk registry format.  Keep both spellings in sync.
    @property
    def model_name(self) -> str:
        return self.name


@dataclass
class GenerationResult:
    """Output of a single ``generate_content`` call."""

    text: str = ""
    images: list[Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.images is None:
            self.images = []


class BaseGeminiClient(ABC):
    """The narrow interface used by the rest of the proxy.

    Implementations must be safe to call concurrently with a single
    instance — the proxy does no additional locking.
    """

    @abstractmethod
    async def init(self, *, timeout: float, auto_refresh: bool) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def list_models(self) -> list[ModelDescriptor]: ...

    @abstractmethod
    async def generate_content(
        self,
        prompt: str,
        *,
        files: list[Any] | None,
        model: Any,
    ) -> GenerationResult: ...
