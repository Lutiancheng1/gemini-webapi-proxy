"""``POST /admin/probe-models`` — re-probe every model and refresh the registry."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends

from gemini_openai_proxy.auth import require_api_key_if_configured
from gemini_openai_proxy.client.pool import registry
from gemini_openai_proxy.config import get_settings
from gemini_openai_proxy.services.probe import probe_all_models

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_api_key_if_configured)],
)


@router.post("/probe-models")
async def admin_probe_models():
    settings = get_settings()
    await probe_all_models(settings)
    return {
        "status": "ok",
        "models": registry.list_openai_models(),
        "updated_at": int(time.time()),
    }
