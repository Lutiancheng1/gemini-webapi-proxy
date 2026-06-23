from __future__ import annotations

import base64
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

DATA_URL_RE = re.compile(r"^data:([^;,]*)(?:;base64)?,(.*)$", re.I | re.S)


def normalize_image_field(value: Any) -> list[str]:
    """Normalize an ``image`` request-body field to a list of URL strings.

    Accepts: ``None`` / single string / list of strings.  Returns a flat list
    of non-empty stripped strings; unknown shapes yield ``[]``.
    """
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
        return out
    return []


def decode_data_url(data_url: str) -> tuple[str, bytes]:
    """Decode ``data:<mime>;base64,<...>`` to ``(mime, bytes)``."""
    m = DATA_URL_RE.match(data_url.strip())
    if not m:
        raise ValueError("Invalid data URL reference image format")
    mime = (m.group(1) or "application/octet-stream").lower()
    raw = m.group(2).strip()
    try:
        data = base64.b64decode(raw, validate=False)
    except Exception as exc:
        raise ValueError("Reference image base64 decode failed") from exc
    if not data:
        raise ValueError("Reference image is empty")
    return mime, data


def _ext_from_mime(mime: str) -> str:
    if "png" in mime:
        return ".png"
    if "jpeg" in mime or "jpg" in mime:
        return ".jpg"
    if "webp" in mime:
        return ".webp"
    if "gif" in mime:
        return ".gif"
    return ".bin"


async def _download_url(url: str, proxy: str | None) -> tuple[str, bytes]:
    async with httpx.AsyncClient(proxy=proxy, timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        mime = (resp.headers.get("content-type") or "image/png").split(";")[0].strip().lower()
        return mime, resp.content


async def materialize_reference_images(
    refs: list[str],
    *,
    proxy: str | None = None,
) -> list[Path]:
    """Turn data URLs / http(s) URLs / local file paths into temp files for upload.

    The returned paths live in a single ``tempfile.mkdtemp(prefix='gemini-ref-')``
    directory; the caller is responsible for cleanup (see
    :func:`cleanup_reference_images`).
    """
    if not refs:
        return []

    tmpdir = Path(tempfile.mkdtemp(prefix="gemini-ref-"))
    paths: list[Path] = []
    for i, ref in enumerate(refs):
        if ref.startswith("data:"):
            mime, data = decode_data_url(ref)
            ext = _ext_from_mime(mime)
            path = tmpdir / f"ref_{i}{ext}"
            path.write_bytes(data)
            paths.append(path)
            continue

        parsed = urlparse(ref)
        if parsed.scheme in {"http", "https"}:
            mime, data = await _download_url(ref, proxy)
            ext = _ext_from_mime(mime)
            path = tmpdir / f"ref_{i}{ext}"
            path.write_bytes(data)
            paths.append(path)
            continue

        local = Path(ref)
        if local.is_file():
            paths.append(local)
            continue

        raise ValueError(f"Unsupported reference image input: {ref[:80]}")

    return paths


def cleanup_reference_images(paths: list[Path]) -> None:
    """Remove a temp directory created by :func:`materialize_reference_images`."""
    if not paths:
        return
    tmp_root = paths[0].parent
    if tmp_root.name.startswith("gemini-ref-"):
        for p in paths:
            p.unlink(missing_ok=True)
        try:
            tmp_root.rmdir()
        except OSError:
            pass
