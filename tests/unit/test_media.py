"""Unit tests for :mod:`gemini_openai_proxy.utils.media`."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from gemini_openai_proxy.utils.media import (
    cleanup_reference_images,
    decode_data_url,
    normalize_image_field,
)


def test_normalize_none_and_empty() -> None:
    assert normalize_image_field(None) == []
    assert normalize_image_field("") == []
    assert normalize_image_field("   ") == []


def test_normalize_string() -> None:
    assert normalize_image_field("data:image/png;base64,AAAA") == ["data:image/png;base64,AAAA"]


def test_normalize_list() -> None:
    out = normalize_image_field(["a", "", "  ", "b"])
    assert out == ["a", "b"]


def test_normalize_unknown_type() -> None:
    assert normalize_image_field({"a": 1}) == []


def test_decode_data_url_ok() -> None:
    payload = base64.b64encode(b"hello").decode()
    mime, data = decode_data_url(f"data:image/png;base64,{payload}")
    assert mime == "image/png"
    assert data == b"hello"


def test_decode_data_url_invalid() -> None:
    with pytest.raises(ValueError):
        decode_data_url("not a data url")


def test_decode_data_url_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        decode_data_url("data:image/png;base64,")


def test_cleanup_reference_images(tmp_path: Path) -> None:
    fake = tmp_path / "fake.png"
    fake.write_bytes(b"x")
    # Put it under a gemini-ref-* subdir
    sub = tmp_path / "gemini-ref-abc"
    sub.mkdir()
    p = sub / "ref_0.png"
    p.write_bytes(b"x")
    cleanup_reference_images([p])
    assert not p.exists()
    assert not sub.exists()
