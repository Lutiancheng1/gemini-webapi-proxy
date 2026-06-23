"""Pluggable cookie source abstraction.

A :class:`BaseCookieSource` is the single place that knows how to obtain a
:class:`CookieBundle` (a tuple of ``__Secure-1PSID``/``__Secure-1PSIDTS`` plus
optional extra cookies).  Concrete implementations live in sibling modules:

* :mod:`.browser` — read from Safari/Chrome/Edge/Brave/Chromium/Firefox
  via ``browser-cookie3`` (default on macOS / desktop)
* :mod:`.env` — read from ``GOP_GEMINI_1PSID`` / ``GOP_GEMINI_1PSIDTS``
  environment variables (default on Linux / server)
* :mod:`.file` — read from a Netscape-format cookie file (new, useful for
  headless servers and CI)

New sources can be added by subclassing :class:`BaseCookieSource` and
registering them in :data:`SOURCES`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CookieBundle:
    """The minimum cookie material needed to talk to Gemini Web."""

    psid: str
    psidts: str
    extras: dict[str, str] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return bool(self.psid)


class BaseCookieSource(ABC):
    """A pluggable source of Gemini Web cookies.

    Subclasses set :attr:`name` (used in config / logs) and implement
    :meth:`load`.  :meth:`health_check` is optional; the default does a
    single chat probe via the Gemini Web RPC.
    """

    name: str = "abstract"

    @abstractmethod
    async def load(self) -> CookieBundle: ...

    async def health_check(self, bundle: CookieBundle, proxy: str | None) -> bool:
        """Default: probe with a tiny chat request.  Override for speed."""
        try:
            from gemini_webapi import GeminiClient
            from gemini_webapi.constants import AccountStatus

            client = GeminiClient(bundle.psid, bundle.psidts, proxy=proxy)
            if bundle.extras:
                client.cookies = dict(bundle.extras)
            await client.init(timeout=60, auto_refresh=True)
            ok = client.account_status == AccountStatus.AVAILABLE or bool(client.access_token)
            await client.close()
            return ok
        except Exception:
            return False


# Registry of available sources.  Add new sources here.
SOURCES: dict[str, type[BaseCookieSource]] = {}


def register_source(cls: type[BaseCookieSource]) -> type[BaseCookieSource]:
    """Class decorator that adds a cookie source to :data:`SOURCES`."""
    SOURCES[cls.name] = cls
    return cls


def build_source(name: str, **kwargs: object) -> BaseCookieSource:
    """Instantiate a registered cookie source by name."""
    if name not in SOURCES:
        raise ValueError(f"Unknown cookie source: {name!r}. Available: {sorted(SOURCES)}")
    return SOURCES[name](**kwargs)
