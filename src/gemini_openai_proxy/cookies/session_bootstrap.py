from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_DIR_NAMES = ("gemini_webapi",)
_CACHE_GLOB = ".cached_cookies_*.json"


def _candidate_cache_dirs() -> list[Path]:
    dirs: list[Path] = []
    tmp = Path(tempfile.gettempdir())
    for name in _CACHE_DIR_NAMES:
        dirs.append(tmp / name)
    # gemini_webapi also uses macOS /var/folders/.../T via tempfile
    var_tmp = Path("/var/folders")
    if var_tmp.is_dir():
        try:
            for entry in var_tmp.iterdir():
                candidate = entry / "T" / "gemini_webapi"
                if candidate.is_dir():
                    dirs.append(candidate)
        except OSError:
            pass
    return dirs


def clear_stale_gemini_webapi_cookie_cache(*, psid: str | None = None) -> int:
    """
    gemini-webapi merges `.cached_cookies_<psid>.json` over live browser cookies.
    Stale cache entries often drop SNlM0e (access_token), which breaks image generation
    even when Safari/Chrome is still logged in.
    """
    removed = 0
    seen: set[Path] = set()
    for cache_dir in _candidate_cache_dirs():
        if not cache_dir.is_dir():
            continue
        patterns = [_CACHE_GLOB]
        if psid:
            patterns.append(f".cached_cookies_{psid}.json")
        for pattern in patterns:
            for path in cache_dir.glob(pattern):
                if path in seen:
                    continue
                seen.add(path)
                try:
                    path.unlink()
                    removed += 1
                    logger.info("Removed stale gemini-webapi cookie cache: %s", path)
                except OSError as exc:
                    logger.warning("Could not remove cookie cache %s: %s", path, exc)
    return removed


def bootstrap_browser_cookie_session(*, psid: str | None = None) -> None:
    """Prepare browser-cookie mode before gemini-webapi init."""
    if os.getenv("GEMINI_WEBAPI_KEEP_COOKIE_CACHE", "").lower() in {"1", "true", "yes"}:
        return
    clear_stale_gemini_webapi_cookie_cache(psid=psid)
