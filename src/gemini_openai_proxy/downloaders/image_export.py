"""Shared helpers used by all downloaders.

THIS MODULE IS A TRANSITIONAL SHIM. In phase 1.F the inline download chain
lives in :mod:`gemini_openai_proxy.downloaders.chain` and each individual
strategy becomes a :class:`BaseDownloader` subclass.

Only the small helpers used by the httpx/playwright downloaders stay here
for now: cookie sanitization, request headers, CDN proxy decision, and
``=d-I?alr=yes`` candidate generation.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from gemini_webapi.constants import Headers

from gemini_openai_proxy.config import Settings

# ---- Constants -----------------------------------------------------------
_GG_DL_MARKERS = ("gg-dl", "googleusercontent.com", "usercontent.google.com")
_CDN_HOST_MARKERS = ("googleusercontent.com", "usercontent.google.com")
_DOWNLOAD_COOKIE_BLOCKLIST = frozenset(
    {
        "COMPASS",
        "NID",
        "AEC",
        "1P_JAR",
        "DV",
        "__Secure-ENID",
    }
)
_DOWNLOAD_COOKIE_ALLOWLIST = frozenset(
    {
        "__Secure-1PSID",
        "__Secure-1PSIDTS",
        "__Secure-1PSIDCC",
        "__Secure-3PSID",
        "__Secure-3PSIDTS",
        "__Secure-3PAPISID",
        "SAPISID",
        "APISID",
        "HSID",
        "SSID",
        "SID",
        "SIDCC",
    }
)
_GOOGLE_COOKIE_DOMAINS = (
    ".google.com",
    ".google.com.hk",
    ".gemini.google.com",
    "gemini.google.com",
)


# ---- Pure helpers --------------------------------------------------------
def _keep_download_cookie(name: str, value: str) -> bool:
    if not value or name in _DOWNLOAD_COOKIE_BLOCKLIST:
        return False
    return name in _DOWNLOAD_COOKIE_ALLOWLIST or name.startswith(
        ("__Secure-1PSID", "__Secure-3PSID")
    )


def _sanitize_download_cookies(cookie_map: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in cookie_map.items() if _keep_download_cookie(k, v)}


def _is_gg_dl_url(url: str) -> bool:
    lower = url.lower()
    return any(marker in lower for marker in _GG_DL_MARKERS)


def _download_candidates(url: str) -> list[str]:
    cleaned = url.strip()
    if not cleaned:
        return []
    out = [cleaned]
    if _is_gg_dl_url(cleaned) and "=d-I" not in cleaned:
        out.append(f"{cleaned}=d-I?alr=yes")
    return out


def _size_fallback_url(url: str, *, full_size: bool = True) -> str:
    if full_size:
        if "=s1024-rj" in url:
            return url.replace("=s1024-rj", "=s2048-rj")
        if "=s2048-rj" not in url:
            return url + "=s2048-rj"
        return url
    if "=s2048-rj" in url:
        return url.replace("=s2048-rj", "=s1024-rj")
    if "=s1024-rj" not in url:
        return url + "=s1024-rj"
    return url


def _impersonate(settings: Settings) -> str:
    if settings.browser == "safari":
        return "safari184"
    return "chrome131"


def _cdn_proxy(settings: Settings, url: str) -> str | None:
    """Bypass the user proxy for Google CDN domains.

    Google CDN hops after ``gg-dl`` often break when forced through a local
    MITM/Clash proxy. Gemini API traffic still uses ``HTTP_PROXY``; CDN
    downloads go direct.
    """
    if not settings.cdn_direct:
        return settings.http_proxy
    host = urlparse(url).hostname or ""
    if any(marker in host for marker in _CDN_HOST_MARKERS):
        return None
    return settings.http_proxy


def _download_headers(*, referer: str | None = None) -> dict[str, str]:
    hdr = dict(Headers.REFERER.value)
    if referer:
        hdr["Referer"] = referer
    return hdr


# ---- Client cookie jar management ---------------------------------------
def _purge_tracking_cookies(jar: Any) -> None:
    if jar is None:
        return
    names = set(_DOWNLOAD_COOKIE_BLOCKLIST) | {"__Secure-STRP", "__Secure-BUCKET"}
    for name in names:
        for domain in _GOOGLE_COOKIE_DOMAINS:
            try:
                jar.delete(name, domain=domain)
            except Exception:
                pass


def _cookie_jar(client: Any) -> dict[str, str]:
    inner = getattr(getattr(client, "client", None), "cookies", None)
    if inner is not None:
        _purge_tracking_cookies(inner)
        if hasattr(inner, "get_dict"):
            try:
                return dict(inner.get_dict())
            except Exception:
                pass
    raw = client.cookies
    if hasattr(raw, "get_dict"):
        try:
            return dict(raw.get_dict())
        except Exception:
            pass
    try:
        return dict(raw)
    except Exception:
        try:
            return {k: raw[k] for k in raw}
        except Exception:
            return {}


def sanitize_gemini_client_cookies(client: Any) -> dict[str, str]:
    """Strip tracking cookies that break curl_cffi after Gemini RPC refreshes."""
    inner = getattr(client, "client", None)
    if inner is not None:
        _purge_tracking_cookies(getattr(inner, "cookies", None))
    clean = _sanitize_download_cookies(_cookie_jar(client))
    try:
        client.cookies = clean
    except Exception:
        pass
    return clean


# ---- Session management -------------------------------------------------
def _is_session_closed_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return ("session is closed" in msg) or ("cannot send request" in msg)


def _reset_download_cookies(session: Any, cookie_map: dict[str, str]) -> None:
    jar = getattr(session, "cookies", None)
    if jar is None:
        return
    try:
        jar.clear()
    except Exception:
        pass
    for name, value in cookie_map.items():
        try:
            jar.set(name, value)
        except Exception:
            try:
                jar[name] = value
            except Exception:
                pass


# ---- RPC URL resolver ----------------------------------------------------
async def _resolve_rpc_start(image: Any, client: Any) -> str | None:
    """Return the RPC full-size URL (``<url>=d-I?alr=yes``), or ``None`` if the
    image doesn't carry the necessary identifiers (cid/rid/rcid/image_id)."""
    if not all(
        [
            getattr(image, "client_ref", None),
            getattr(image, "cid", None),
            getattr(image, "rid", None),
            getattr(image, "rcid", None),
            getattr(image, "image_id", None),
        ]
    ):
        return None
    try:
        original_url = await client._get_full_size_image(
            cid=image.cid,
            rid=image.rid,
            rcid=image.rcid,
            image_id=image.image_id,
        )
    except Exception:
        return None
    if not original_url:
        return None
    return f"{original_url}=d-I?alr=yes"
