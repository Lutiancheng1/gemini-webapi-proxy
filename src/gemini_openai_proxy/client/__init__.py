"""Gemini client abstraction.

The public API used by the rest of the codebase is the concrete
:class:`gemini_webapi.GeminiClient` (returned by :func:`client.pool.get_client`).
:class:`BaseGeminiClient` is the narrow interface future backends (REST,
test mocks) should implement; :class:`WebAPIClient` is a working
adapter that wraps the real client.
"""

from __future__ import annotations

from gemini_openai_proxy.client.base import (
    BaseGeminiClient,
    GenerationResult,
    ModelDescriptor,
)
from gemini_openai_proxy.client.webapi import WebAPIClient

__all__ = [
    "BaseGeminiClient",
    "GenerationResult",
    "ModelDescriptor",
    "WebAPIClient",
]
