#!/usr/bin/env python3
"""02 — One text-to-image generation, save PNG.

Uses the stable gemini-2.5-flash-image alias. Writes the decoded PNG
to out.png next to this script.
"""
import base64
import os
import pathlib

from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("GOP_BASE_URL", "http://localhost:4982/openai/v1"),
    api_key=os.getenv("GOP_API_KEY", "not-verified"),
)

img = client.images.generate(
    model="gemini-2.5-flash-image",
    prompt="a single orange on a white plate, soft natural light, photorealistic",
    n=1,
    response_format="b64_json",
)

out = pathlib.Path(__file__).parent / "out.png"
out.write_bytes(base64.b64decode(img.data[0].b64_json))
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
