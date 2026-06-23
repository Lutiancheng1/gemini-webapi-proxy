#!/usr/bin/env python3
"""Probe every account model and write the result to data/model_registry.json."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gemini_webapi_proxy.client.pool import close_client, get_client, registry  # noqa: E402
from gemini_webapi_proxy.config import get_settings  # noqa: E402
from gemini_webapi_proxy.services.probe import probe_all_models  # noqa: E402


async def main() -> None:
    settings = get_settings()
    await get_client(settings)
    print(f"Account models: {len(registry.entries)}, probing...")
    await probe_all_models(settings)
    print("Done, writing data/model_registry.json")
    registry.save_file()
    for entry in sorted(registry.entries, key=lambda e: e.id):
        print(f"- {entry.id}: kind={entry.kind} chat={entry.chat_ok} image={entry.image_ok}")
    await close_client()


if __name__ == "__main__":
    asyncio.run(main())
