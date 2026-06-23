from __future__ import annotations

import asyncio
import re
import time
import uuid
from pathlib import Path

from gemini_webapi.types.image import GeneratedImage

from gemini_openai_proxy.client.pool import get_client, registry
from gemini_openai_proxy.config import Settings
from gemini_openai_proxy.downloaders.chain import generated_image_to_b64
from gemini_openai_proxy.downloaders.image_export import sanitize_gemini_client_cookies
from gemini_openai_proxy.schemas import (
    ChatCompletionChoice,
    ChatCompletionResponse,
    ChatMessage,
    ImageGenerationData,
    ImageGenerationResponse,
)
from gemini_openai_proxy.utils.media import materialize_reference_images, normalize_image_field

QUOTA_PATTERNS = (
    r"limit resets",
    r"usage in settings",
    r"额度",
    r"重置",
    r"使用情况",
)


def _quota_message(text: str) -> bool:
    blob = text.lower()
    return any(re.search(p, blob, re.I) for p in QUOTA_PATTERNS)


def _messages_to_prompt_and_refs(messages: list[ChatMessage]) -> tuple[str, list[str]]:
    chunks: list[str] = []
    refs: list[str] = []
    for msg in messages:
        role = msg.role.upper()
        if isinstance(msg.content, str):
            chunks.append(f"{role}: {msg.content}")
            continue
        text_parts: list[str] = []
        for part in msg.content:
            ptype = (part.get("type") or "").lower()
            if ptype == "text":
                text_parts.append(part.get("text", ""))
            elif ptype in {"image_url", "input_image"}:
                url_part = part.get("image_url") or {}
                url = url_part.get("url") if isinstance(url_part, dict) else str(url_part)
                if url:
                    refs.append(url)
        chunks.append(f"{role}: {' '.join(text_parts)}")
    return "\n\n".join(chunks), refs


def _image_prompt(prompt: str, size: str | None, *, has_reference: bool) -> str:
    if has_reference:
        body = (
            "Use the attached reference image(s) as visual reference (character, style, composition, or subject). "
            "Generate a new image based on the reference and the prompt below. "
            "Return the generated image, not only text.\n\n"
            f"Prompt: {prompt.strip()}"
        )
    else:
        body = (
            "Generate an image from this prompt. Return the generated image, not only text.\n\n"
            f"Prompt: {prompt.strip()}"
        )
    if size:
        body += f"\nRequested size/aspect: {size}"
    return body


async def _image_to_b64(image: GeneratedImage, settings: Settings, client) -> str:
    return await generated_image_to_b64(image, settings=settings, client=client)


async def create_chat_completion(
    settings: Settings,
    *,
    model: str,
    messages: list[ChatMessage],
) -> ChatCompletionResponse:
    client = await get_client(settings)
    resolved = registry.resolve_id(model)
    runtime = registry.resolve_runtime(resolved)
    prompt, msg_refs = _messages_to_prompt_and_refs(messages)
    ref_paths: list[Path] = []
    if msg_refs:
        ref_paths = await materialize_reference_images(msg_refs, proxy=settings.http_proxy)
    try:
        output = await asyncio.wait_for(
            client.generate_content(
                prompt,
                files=ref_paths or None,
                model=runtime,
            ),
            timeout=settings.chat_timeout,
        )
        text = (output.text or "").strip()
        images = output.images or []
        content: str | list[dict] = text
        if images and not text:
            content = text
        payload: dict = {"role": "assistant", "content": content}
        if images:
            payload["images"] = [{"url": img.url} for img in images]
        if _quota_message(text) and not images:
            raise RuntimeError(text)
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=resolved,
            choices=[ChatCompletionChoice(message=payload)],
        )
    finally:
        if ref_paths:
            tmp_root = ref_paths[0].parent
            if tmp_root.name.startswith("gemini-ref-"):
                for p in ref_paths:
                    p.unlink(missing_ok=True)
                tmp_root.rmdir()


async def create_image_generation(
    settings: Settings,
    *,
    model: str,
    prompt: str,
    n: int,
    size: str | None,
    response_format: str | None,
    reference_images: list[str] | None = None,
) -> ImageGenerationResponse:
    client = await get_client(settings)
    target = registry.pick_image_model(model)
    runtime = registry.resolve_runtime(target)
    refs = normalize_image_field(reference_images)
    ref_paths: list[Path] = []
    if refs:
        ref_paths = await materialize_reference_images(refs, proxy=settings.http_proxy)
    data: list[ImageGenerationData] = []
    attempts = 0
    max_attempts = max(n, 1) + 2
    try:
        while len(data) < n and attempts < max_attempts:
            attempts += 1
            sanitize_gemini_client_cookies(client)
            output = await asyncio.wait_for(
                client.generate_content(
                    _image_prompt(prompt, size, has_reference=bool(ref_paths)),
                    files=ref_paths or None,
                    model=runtime,
                ),
                timeout=settings.image_timeout,
            )
            text = (output.text or "").strip()
            images = output.images or []
            if not images:
                if _quota_message(text):
                    raise RuntimeError(text)
                if text:
                    raise RuntimeError(text)
                raise RuntimeError(
                    "Gemini returned no image (the model path may not match; "
                    "try a different model or check GET /openai/v1/models)"
                )
            for img in images:
                if len(data) >= n:
                    break
                sanitize_gemini_client_cookies(client)
                # Always return b64_json: Google CDN URLs are not fetchable by downstream clients.
                data.append(
                    ImageGenerationData(
                        revised_prompt=prompt,
                        b64_json=await _image_to_b64(img, settings, client),
                    )
                )
    finally:
        if ref_paths:
            tmp_root = ref_paths[0].parent
            if tmp_root.name.startswith("gemini-ref-"):
                for p in ref_paths:
                    p.unlink(missing_ok=True)
                tmp_root.rmdir()
    return ImageGenerationResponse(created=int(time.time()), data=data)
