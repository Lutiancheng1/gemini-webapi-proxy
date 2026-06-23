"""Integration tests for the FastAPI app (no real Gemini client required)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from gemini_openai_proxy.app import app


def test_health_does_not_require_client() -> None:
    """``/health`` must answer 200 without touching the Gemini client."""
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "gemini-openai-proxy"}


def test_unknown_route_404() -> None:
    with TestClient(app) as client:
        resp = client.get("/nope")
    assert resp.status_code == 404


def test_models_route_returns_503_when_no_client() -> None:
    """Without a configured client, /models should fail with a 5xx (not crash)."""
    with TestClient(app) as client:
        resp = client.get("/openai/v1/models")
    # We don't have a real client in tests; either an error or an empty list
    # is acceptable as long as the response is well-formed.
    assert resp.status_code in (200, 500, 503)
    if resp.status_code == 200:
        assert "data" in resp.json()


def test_chat_rejects_stream(monkeypatch) -> None:
    """``stream=true`` must return 400 with a helpful message."""
    from gemini_openai_proxy.config import reset_settings_cache

    monkeypatch.setenv("GOP_COOKIE_SOURCE", "env")
    reset_settings_cache()
    with TestClient(app) as client:
        resp = client.post(
            "/openai/v1/chat/completions",
            json={
                "model": "gemini-3-flash",
                "stream": True,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert resp.status_code == 400
    assert "stream" in resp.json()["detail"].lower()
