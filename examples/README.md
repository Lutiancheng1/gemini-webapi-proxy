# Examples

Runnable code samples showing how to use `gemini-webapi-proxy` from a
client. Each file is a self-contained script — copy it, set
`GOP_API_KEY` if you enabled auth, and `python` it.

| # | File | What it does |
|---|------|--------------|
| 01 | [`01_chat_basic.py`](01_chat_basic.py) | One chat completion through the proxy |
| 02 | [`02_image_basic.py`](02_image_basic.py) | One text-to-image generation, save PNG |
| 03 | [`03_image_with_reference.py`](03_image_with_reference.py) | Image-to-image with a reference photo |
| 04 | [`04_outsider_studio.md`](04_outsider_studio.md) | Connect Outsider Studio (the GUI client) |

## Before running

```bash
# Make sure the proxy is up
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-webapi-proxy"}
```

Each script defaults to `http://localhost:4982/openai/v1` and accepts
two env vars:

- `GOP_BASE_URL` (default: `http://localhost:4982/openai/v1`)
- `GOP_API_KEY` (default: `not-verified` — any non-empty string when
  the proxy is running without `GOP_API_KEY` set; otherwise the real key)
