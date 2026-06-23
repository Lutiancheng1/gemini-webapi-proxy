"""``GET /openai/v1/models`` — list models visible to OpenAI clients."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from gemini_webapi_proxy.auth import require_api_key_if_configured
from gemini_webapi_proxy.client.pool import registry
from gemini_webapi_proxy.config import get_settings
from gemini_webapi_proxy.schemas import ModelListResponse, ModelObject

router = APIRouter(
    prefix="/openai/v1",
    tags=["models"],
    dependencies=[Depends(require_api_key_if_configured)],
)


@router.get("/models", response_model=ModelListResponse)
async def list_models() -> ModelListResponse:
    settings = get_settings()
    overrides = set(settings.image_model_overrides or [])
    items = registry.list_openai_models(image_overrides=overrides)
    return ModelListResponse(data=[ModelObject(**item) for item in items])
