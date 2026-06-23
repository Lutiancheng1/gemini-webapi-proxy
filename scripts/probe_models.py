#!/usr/bin/env python3
"""批量探测账号可用模型，写入 data/model_registry.json"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gemini_openai_proxy.config import get_settings
from gemini_openai_proxy.gemini_pool import close_client, get_client, registry
from gemini_openai_proxy.services.probe import probe_all_models


async def main() -> None:
    settings = get_settings()
    await get_client(settings)
    print(f"账号模型 {len(registry.entries)} 个，开始探测…")
    await probe_all_models(settings)
    print("完成，写入 data/model_registry.json")
    registry.save_file()
    for entry in sorted(registry.entries, key=lambda e: e.id):
        print(
            f"- {entry.id}: kind={entry.kind} chat={entry.chat_ok} image={entry.image_ok}"
        )
    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
