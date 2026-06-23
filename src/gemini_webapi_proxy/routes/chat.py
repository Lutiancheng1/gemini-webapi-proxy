"""``POST /openai/v1/chat/completions`` — non-streaming chat."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from gemini_webapi_proxy.auth import require_api_key_if_configured
from gemini_webapi_proxy.config import get_settings
from gemini_webapi_proxy.schemas import ChatCompletionRequest, ChatCompletionResponse
from gemini_webapi_proxy.services.chat import create_chat_completion

router = APIRouter(
    prefix="/openai/v1",
    tags=["chat"],
    dependencies=[Depends(require_api_key_if_configured)],
)


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(body: ChatCompletionRequest):
    if body.stream:
        raise HTTPException(
            status_code=400,
            detail="stream=true is not implemented yet. Set stream=false (see README §Roadmap).",
        )
    settings = get_settings()
    try:
        return await create_chat_completion(settings, model=body.model, messages=body.messages)
    except asyncio.TimeoutError:
        from gemini_webapi_proxy.routes._errors import error_json

        return error_json("Request timed out", 504)
    except Exception as exc:
        from gemini_webapi_proxy.routes._errors import map_api_error

        return await map_api_error(exc, settings)
