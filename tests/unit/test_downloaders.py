"""Unit tests for the image downloader machinery."""

from __future__ import annotations

from gemini_webapi_proxy.downloaders import all_downloaders
from gemini_webapi_proxy.downloaders.image_export import (
    _download_candidates,
    _is_gg_dl_url,
    _is_session_closed_error,
    _sanitize_download_cookies,
    _size_fallback_url,
)


def test_is_gg_dl_url() -> None:
    assert _is_gg_dl_url("https://lh3.googleusercontent.com/gg-dl/AFfU-fJ")
    assert _is_gg_dl_url("https://work.fife.usercontent.google.com/rd-gg-dl/x")
    assert not _is_gg_dl_url("https://example.com/image.png")


def test_download_candidates_adds_alr_suffix() -> None:
    base = "https://lh3.googleusercontent.com/gg-dl/abc"
    cands = _download_candidates(base)
    assert cands[0] == base
    assert cands[1] == base + "=d-I?alr=yes"


def test_download_candidates_skips_duplicate_suffix() -> None:
    url = "https://lh3.googleusercontent.com/gg-dl/abc=d-I?alr=yes"
    assert _download_candidates(url) == [url]


def test_size_fallback_url_full_size() -> None:
    base = "https://lh3.googleusercontent.com/gg-dl/abc"
    assert _size_fallback_url(base).endswith("=s2048-rj")
    assert _size_fallback_url(base + "=s1024-rj") == base + "=s2048-rj"


def test_size_fallback_url_preview() -> None:
    base = "https://lh3.googleusercontent.com/gg-dl/abc"
    assert _size_fallback_url(base, full_size=False).endswith("=s1024-rj")


def test_session_closed_detection() -> None:
    assert _is_session_closed_error(RuntimeError("Session is closed, cannot send request."))
    assert not _is_session_closed_error(RuntimeError("403 Forbidden"))


def test_sanitize_download_cookies() -> None:
    raw = {
        "__Secure-1PSID": "a",
        "COMPASS": "b",  # blocklist
        "SAPISID": "c",  # allowlist
        "NID": "d",  # blocklist
        "AEC": "e",  # blocklist
        "random_tracker": "f",  # not in either -> drop
        "NID_EMPTY": "",  # empty value -> drop
    }
    out = _sanitize_download_cookies(raw)
    assert out == {"__Secure-1PSID": "a", "SAPISID": "c"}


def test_all_five_downloaders_registered() -> None:
    expected = {
        "playwright-rpc",
        "playwright-preview",
        "httpx-rpc",
        "httpx-preview",
        "library-save",
    }
    assert expected.issubset(all_downloaders().keys())


def test_downloader_priorities_are_distinct() -> None:
    classes = list(all_downloaders().values())
    seen = {c.priority for c in classes}
    assert len(seen) == len(classes), "priorities must be unique"
