"""Read cookies from a Netscape-format cookie file.

Format (one cookie per line, tab-separated)::

    domain  flag  path  secure  expires  name  value

Lines starting with ``#`` and blank lines are ignored.  This is the same
format used by ``curl``, ``wget``, and most browser cookie-export tools
(``cookies.txt`` from "Get cookies.txt LOCALLY" extension, etc.).
"""

from __future__ import annotations

from pathlib import Path

from gemini_webapi_proxy.config import get_settings
from gemini_webapi_proxy.cookies.base import BaseCookieSource, CookieBundle, register_source


@register_source
class FileCookieSource(BaseCookieSource):
    """Read cookies from a Netscape-format ``cookies.txt`` file."""

    name = "file"

    def __init__(self, path: Path | None = None) -> None:
        s = get_settings()
        self._path = path or s.cookie_file
        if not self._path:
            raise RuntimeError(
                "GOP_COOKIE_FILE is empty. Set it to a Netscape-format cookies.txt path."
            )

    async def load(self) -> CookieBundle:
        path = Path(self._path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Cookie file not found: {path}")

        cookie_map: dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # Netscape: domain, flag, path, secure, expires, name, value
            # Some exports prefix lines with `HttpOnly_` — strip that.
            if line.startswith("HttpOnly_"):
                line = line[len("HttpOnly_") :]
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            name, value = parts[5], parts[6]
            if name:
                cookie_map[name] = value

        psid = cookie_map.get("__Secure-1PSID", "")
        if not psid:
            raise RuntimeError(
                f"Cookie file {path} has no __Secure-1PSID. "
                "Export from a browser session that is logged in to gemini.google.com."
            )
        psidts = cookie_map.get("__Secure-1PSIDTS", "")
        return CookieBundle(psid=psid, psidts=psidts, extras=cookie_map)
