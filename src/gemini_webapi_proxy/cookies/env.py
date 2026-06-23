"""Read cookies from ``GOP_GEMINI_1PSID`` / ``GOP_GEMINI_1PSIDTS`` env vars."""

from __future__ import annotations

from gemini_webapi_proxy.config import get_settings
from gemini_webapi_proxy.cookies.base import BaseCookieSource, CookieBundle, register_source


@register_source
class EnvCookieSource(BaseCookieSource):
    """Use cookies passed via environment variables (no browser involved)."""

    name = "env"

    async def load(self) -> CookieBundle:
        s = get_settings()
        if not s.gemini_1psid:
            raise RuntimeError(
                "GOP_GEMINI_1PSID is empty. Set GOP_GEMINI_1PSID and "
                "GOP_GEMINI_1PSIDTS, or switch GOP_COOKIE_SOURCE=browser."
            )
        return CookieBundle(
            psid=s.gemini_1psid,
            psidts=s.gemini_1psidts or "",
            extras=dict(s.gemini_cookies),
        )

    async def health_check(self, bundle: CookieBundle, proxy: str | None) -> bool:
        # Env-sourced cookies skip the lightweight chat probe (they were
        # already validated by the user during copy-paste) and let the
        # first real request surface any issue.
        return True
