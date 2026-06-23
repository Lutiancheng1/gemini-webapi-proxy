"""Cookie source registry.

Importing this package triggers registration of all built-in sources.
"""

from __future__ import annotations

from gemini_webapi_proxy.cookies import browser, env, file  # noqa: F401 — side-effect imports
from gemini_webapi_proxy.cookies.base import (
    SOURCES,
    BaseCookieSource,
    CookieBundle,
    build_source,
    register_source,
)

__all__ = [
    "SOURCES",
    "BaseCookieSource",
    "CookieBundle",
    "build_source",
    "register_source",
]
