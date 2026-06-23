"""Unit tests for the API-key auth dependency."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from gemini_openai_proxy.auth import require_api_key_if_configured


def _request(headers: dict[str, str] | None = None):
    """Build a minimal Request stub for the auth dependency."""

    class _Stub:
        def __init__(self, h: dict[str, str]) -> None:
            self.headers = h

    return _Stub(headers or {})


def test_no_key_configured_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.delenv("GOP_API_KEY", raising=False)
    reset_settings_cache()
    # Should not raise
    require_api_key_if_configured(_request())


def test_missing_authorization_header_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_API_KEY", "secret")
    reset_settings_cache()
    with pytest.raises(HTTPException) as ei:
        require_api_key_if_configured(_request())
    assert ei.value.status_code == 401


def test_wrong_token_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_API_KEY", "secret")
    reset_settings_cache()
    with pytest.raises(HTTPException) as ei:
        require_api_key_if_configured(_request({"Authorization": "Bearer wrong"}))
    assert ei.value.status_code == 403


def test_correct_token_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_API_KEY", "secret")
    reset_settings_cache()
    # Should not raise
    require_api_key_if_configured(_request({"Authorization": "Bearer secret"}))


def test_non_bearer_scheme_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_API_KEY", "secret")
    reset_settings_cache()
    with pytest.raises(HTTPException):
        require_api_key_if_configured(_request({"Authorization": "Basic secret"}))
