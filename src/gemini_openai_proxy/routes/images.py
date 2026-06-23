"""``POST /openai/v1/images/generations`` — text-to-image + reference images."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from gemini_openai_proxy.auth import require_api_key_if_configured
from gemini_openai_proxy.config import get_settings
from gemini_openai_proxy.schemas import ImageGenerationRequest, ImageGenerationResponse
from gemini_openai_proxy.services.chat import create_image_generation
from gemini_openai_proxy.utils.media import normalize_image_field

router = APIRouter(
    prefix="/openai/v1",
    tags=["images"],
    dependencies=[Depends(require_api_key_if_configured)],
)


@router.post("/images/generations", response_model=ImageGenerationResponse)
async def image_generations(body: ImageGenerationRequest):
    settings = get_settings()
    refs = normalize_image_field(body.image)
    if not refs and body.extra_body:
        refs = normalize_image_field(body.extra_body.get("image"))
    try:
        return await create_image_generation(
            settings,
            model=body.model,
            prompt=body.prompt,
            n=body.n,
            size=body.size,
            response_format=body.response_format,
            reference_images=refs or None,
        )
    except asyncio.TimeoutError:
        from gemini_openai_proxy.routes._errors import error_json

        return error_json("Image generation timed out", 504)
    except Exception as exc:
        from gemini_openai_proxy.routes._errors import map_api_error

        return await map_api_error(exc, settings)
