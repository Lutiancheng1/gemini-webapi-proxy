"""``GET /health`` and ``GET /ready`` endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from gemini_openai_proxy.client.pool import get_client
from gemini_openai_proxy.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe — always returns ok if the process is up."""
    return {"status": "ok", "service": "gemini-openai-proxy"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    """Readiness probe — returns ok only when the Gemini client is initialised.

    Note: this forces client initialisation on first call, which can take
    up to ``GOP_INIT_TIMEOUT`` seconds.  Configure your orchestrator's
    readiness probe accordingly.
    """
    settings = get_settings()
    try:
        await get_client(settings)
        return {"status": "ok", "client": "ready"}
    except Exception as exc:
        return {"status": "degraded", "client": "error", "detail": str(exc)[:200]}
