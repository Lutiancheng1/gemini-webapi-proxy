from __future__ import annotations

import asyncio

from gemini_openai_proxy.client.pool import get_client, registry
from gemini_openai_proxy.config import Settings


async def probe_all_models(settings: Settings) -> None:
    client = await get_client(settings)
    models = client.list_models() or []
    registry.sync_from_client(models)

    async def probe_one(model_name: str, kind: str) -> None:
        runtime = registry.resolve_runtime(model_name)
        chat_ok = False
        image_ok = False
        if kind != "image":
            try:
                out = await asyncio.wait_for(
                    client.generate_content("Reply with exactly: PONG", model=runtime),
                    timeout=90,
                )
                chat_ok = "PONG" in (out.text or "").upper()
            except Exception:
                chat_ok = False
        try_image = kind in {"image", "both", "chat"} or "flash" in model_name.lower()
        if try_image:
            try:
                out = await asyncio.wait_for(
                    client.generate_content(
                        "Generate an image of a solid red circle on white background.",
                        model=runtime,
                    ),
                    timeout=settings.image_timeout,
                )
                image_ok = bool(out.images)
            except Exception:
                image_ok = False
        registry.update_probe(model_name, chat_ok=chat_ok, image_ok=image_ok)

    tasks = []
    for entry in registry.entries:
        if "tts" in entry.id.lower():
            continue
        tasks.append(probe_one(entry.id, entry.kind))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    registry.save_file()
