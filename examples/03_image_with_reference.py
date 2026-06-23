#!/usr/bin/env python3
"""03 — Image-to-image with a reference photo.

Sends a reference image as a base64 data URL in the request's
`image` field, which the proxy forwards to Gemini Web as an attachment.
Saves the result as out.png.

Drop a reference PNG (e.g. a photo of a person, place, or style) next
to this script as `ref.png` before running.
"""

import base64
import os
import pathlib
import sys

from openai import OpenAI

ref_path = pathlib.Path(__file__).parent / "ref.png"
if not ref_path.exists():
    sys.exit(f"missing {ref_path}; drop a reference PNG next to this script and rerun")

ref_data_url = "data:image/png;base64," + base64.b64encode(ref_path.read_bytes()).decode()

client = OpenAI(
    base_url=os.getenv("GOP_BASE_URL", "http://localhost:4982/openai/v1"),
    api_key=os.getenv("GOP_API_KEY", "not-verified"),
)

img = client.images.generate(
    model="gemini-2.5-pro-image",
    prompt=(
        "a portrait in the same style and lighting as the reference; "
        "preserve the same colour palette and composition"
    ),
    n=1,
    size="1024x1024",
    extra_body={"image": [ref_data_url]},
)

out = pathlib.Path(__file__).parent / "out.png"
out.write_bytes(base64.b64decode(img.data[0].b64_json))
print(f"wrote {out} ({out.stat().st_size:,} bytes)")
