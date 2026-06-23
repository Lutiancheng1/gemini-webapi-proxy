<div align="center">

# 🌐 Gemini WebAPI Proxy

**OpenAI-compatible API gateway for Google Gemini Web — drop-in `base_url` replacement for any OpenAI client.**

[![PyPI](https://img.shields.io/pypi/v/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![CI](https://img.shields.io/github/actions/workflow/status/Lutiancheng1/gemini-webapi-proxy/ci.yml?branch=main)](https://github.com/Lutiancheng1/gemini-webapi-proxy/actions)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Flutiancheng1%2Fgemini--openai--proxy-blue)](https://ghcr.io/Lutiancheng1/gemini-webapi-proxy)

[English](README.md) · [中文](README.zh.md)

</div>

---

## ✨ Features

- 🪄 **Drop-in OpenAI API** — point any OpenAI client (Python SDK, OpenAI CLI, ChatBox, NextChat, LobeChat, [Outsider Studio], etc.) at `http://localhost:4982/openai`
- 💬 **Chat completions** — non-streaming JSON, multi-turn, reference images
- 🖼️ **Image generation** — base64 output only (no CDN URL leakage), text-to-image + reference-image-to-image
- 🍪 **Pluggable cookie sources** — desktop browser (Safari/Chrome/...), env vars, Netscape cookie file
- 🐳 **One-command Docker** — `docker compose up -d`, auto-restart, host network bridge for the local proxy
- 🔌 **Multi-fallback image download** — Playwright Chromium, httpx, curl_cffi, library-internal save
- 🛠️ **Optional API key** — `GOP_API_KEY=...` enables Bearer auth; empty = off (local-only default)
- 📋 **Model registry** — discovers, probes, aliases, exposes `/openai/v1/models`

> **Disclaimer:** This project is not affiliated with Google. It uses
> [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API), a reverse-
> engineered client of the Gemini Web frontend. Using it is subject to
> Google's Terms of Service. You are responsible for your own usage.

## 🚀 Quick Start

### Option A: `pip` (PyPI)

```bash
pip install "gemini-webapi-proxy[browser-cookie]"
gemini-webapi-proxy
```

### Option B: From source

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
./start.sh
```

### Option C: Docker

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
bash scripts/docker-up.sh
```

The script copies your browser's Gemini cookies into `data/runtime.env`
(only needed on macOS — Linux hosts can use env vars directly), then
launches the container.

In all three cases, verify the service:

```bash
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-webapi-proxy"}
```

## 🔌 Wiring a client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4982/openai/v1",
    api_key="not-verified",  # any non-empty string; or set GOP_API_KEY
)

resp = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
)
print(resp.choices[0].message.content)
```

For image generation with a reference image:

```python
import base64, pathlib
data_url = "data:image/png;base64," + base64.b64encode(pathlib.Path("ref.png").read_bytes()).decode()

img = client.images.generate(
    model="gemini-3-flash",
    prompt="a portrait in the same style as the reference",
    n=1, size="1024x1024",
    extra_body={"image": [data_url]},
)
pathlib.Path("out.png").write_bytes(base64.b64decode(img.data[0].b64_json))
```

See [docs/studio.md](docs/studio.md) for connecting OpenAI-compatible
desktop apps, and [docs/api.md](docs/api.md) for the full API reference.

## ⚙️ Configuration

All configuration is via environment variables. The `GOP_` prefix is
recommended; a few unprefixed names (`PORT`, `USE_BROWSER_COOKIES`, ...)
are kept as legacy aliases for compatibility.

| Variable | Default | Description |
|----------|---------|-------------|
| `GOP_PORT` | `4982` | listen port |
| `GOP_HOST` | `0.0.0.0` | listen address |
| `GOP_API_KEY` | _(empty)_ | when set, require `Authorization: Bearer <key>` |
| `GOP_COOKIE_SOURCE` | `browser` | `browser` / `env` / `file` |
| `GOP_BROWSER` | `auto` | preferred browser: `auto` / `safari` / `chrome` / `edge` / `brave` / `chromium` |
| `GOP_COOKIE_FILE` | _(empty)_ | path to a Netscape-format cookies.txt |
| `GOP_GEMINI_1PSID` | _(empty)_ | `__Secure-1PSID` value (env / file modes) |
| `GOP_GEMINI_1PSIDTS` | _(empty)_ | `__Secure-1PSIDTS` value |
| `GOP_GEMINI_COOKIES_RAW` | _(empty)_ | `k1=v1; k2=v2` form |
| `GOP_HTTP_PROXY` | _(empty)_ | local HTTP proxy (`http://127.0.0.1:7897`) |
| `GOP_CHAT_TIMEOUT` | `180` | seconds |
| `GOP_IMAGE_TIMEOUT` | `300` | seconds |
| `GOP_INIT_TIMEOUT` | `120` | seconds |
| `GOP_PROBE_ON_START` | `false` | probe models at startup |
| `GOP_LOG_FORMAT` | `console` | `console` (dev) or `json` (container) |
| `GOP_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `GOP_DATA_DIR` | `./data` | where the model registry file lives |

See [docs/configuration.md](docs/configuration.md) for the full list and
detailed semantics.

## 🏗️ Architecture

```
┌─────────────── FastAPI (uvicorn) ───────────────┐
│  /health    /ready                              │
│  /openai/v1/models  /openai/v1/chat/completions │
│  /openai/v1/images/generations  /admin/probe-models │
│                                                 │
│  ┌─────────────┐   ┌──────────────────┐         │
│  │ Cookie      │ → │ GeminiClient pool│ → gemini-webapi
│  │ Source      │   │ (lazy singleton) │         │
│  └─────────────┘   └──────────────────┘         │
│                                                 │
│  ┌────────────────────────── Image download ──┐ │
│  │ Playwright Chromium  →  httpx  →  curl_cffi │ │
│  │ →  gemini-webapi library save (last resort)│ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

- **Pluggable cookie sources** (`gemini_webapi_proxy.cookies`) — add a new
  one by subclassing `BaseCookieSource` and registering it.
- **Pluggable image downloaders** (`gemini_webapi_proxy.downloaders`) —
  each strategy is a small class; reorder the chain in `GOP_DOWNLOADER_CHAIN`.
- **Pluggable Gemini client** (`gemini_webapi_proxy.client`) — current
  implementation wraps `gemini-webapi`; future backends can implement
  `BaseGeminiClient` without touching the rest of the code.

## 🛣️ Roadmap

- [ ] **Streaming chat completions** (SSE) — currently `stream=true` returns 400
- [ ] **Pluggable Gemini backends** — official Gemini API, third-party proxies
- [ ] **More cookie sources** — Playwright storage state export, Firefox via `browser-cookie3`
- [ ] **Per-model rate limits** — token-bucket per model id
- [ ] **Hot-reload of model registry** — watch `data/model_registry.json`
- [ ] **Prometheus `/metrics` endpoint**

## 🧪 Development

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
.venv/bin/pytest tests/ -v
.venv/bin/ruff check
.venv/bin/ruff format
.venv/bin/mypy src/
bash scripts/e2e-image.sh  # requires a real Gemini session
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow.

## ⚖️ License

This project is licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE).

It depends on [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API),
which is also GPL-3.0. By installing the runtime dependency, you agree to
its license.

The project is **not affiliated with Google** and provides no warranty.
Use it only in compliance with Google's Terms of Service.

## 🙏 Acknowledgements

- [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) —
  the upstream reverse-engineered client without which this project
  would not exist
- The OpenAI Python SDK team — for a clean, widely-implemented API
  contract that makes this kind of gateway easy to build

[Outsider Studio]: https://github.com/outsider-studio
