# OpenAI-Compatible Client Integration

This proxy speaks the OpenAI HTTP API. Any client that supports a
**custom OpenAI base URL** can be pointed at it. Below is one
worked example; the same settings work for OpenAI's official Python
SDK, `openai-cli`, `ChatBox`, `NextChat`, `LobeChat`, and others.

## Settings (worked example)

| Field | Value |
|-------|-------|
| Provider | Custom OpenAI-compatible (or "OpenAI" with a custom base URL) |
| Base URL | `http://localhost:4982/openai` |
| API Key | Any non-empty string (e.g. `test`). The proxy does not verify it by default. |
| Chat model | `gemini-3-flash` (or any id returned by `/openai/v1/models`) |
| Image model | `gemini-3-flash` / `gemini-3-pro` (same list) |

> The Base URL **must end with `/openai`**. Most clients append
> `/v1/chat/completions` and `/v1/images/generations` automatically.

## Response Conventions

- **Images**: only `b64_json` is returned. Google CDN `url` is
  intentionally not exposed, because downstream clients cannot
  usually fetch `lh3.googleusercontent.com/...` links.
- **Chat**: `stream=false` only in this version. Streaming is on the
  roadmap — see [README.md §Roadmap](../README.md#roadmap).
- **Reference images**: send as the request body's `image` field
  (data URL array). The proxy forwards them as attachments to
  Gemini Web.

## Concurrency

The proxy runs a single shared `GeminiClient` per process; there is
no request queue. Set your client's image generation concurrency to
**1–2** to avoid cookie-refresh storms that surface as 500/401.

## Smoke Test

After starting the proxy, verify the health endpoint:

```bash
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-openai-proxy"}
```

Then trigger a simple chat completion through your client to confirm
end-to-end wiring before relying on it for real work.

## Using the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4982/openai/v1",
    api_key="not-verified",  # any non-empty string
)

resp = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
)
print(resp.choices[0].message.content)
```

## Reference-image example

```python
import base64, pathlib
from openai import OpenAI

img_b64 = base64.b64encode(pathlib.Path("ref.png").read_bytes()).decode()
data_url = f"data:image/png;base64,{img_b64}"

client = OpenAI(base_url="http://localhost:4982/openai/v1", api_key="x")
resp = client.images.generate(
    model="gemini-3-flash",
    prompt="a portrait in the same style as the reference",
    n=1,
    size="1024x1024",
    extra_body={"image": [data_url]},
)
import base64 as b
pathlib.Path("out.png").write_bytes(b.b64decode(resp.data[0].b64_json))
```
