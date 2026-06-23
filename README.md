<div align="center">

# 🌐 Gemini WebAPI Proxy

**OpenAI-compatible reverse-engineered gateway to Google Gemini Web (chat + image gen).**
Drop-in `base_url` replacement for any OpenAI client — **no API key, reuses your browser login**.

[![PyPI](https://img.shields.io/pypi/v/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![CI](https://img.shields.io/github/actions/workflow/status/Lutiancheng1/gemini-webapi-proxy/ci.yml?branch=main)](https://github.com/Lutiancheng1/gemini-webapi-proxy/actions)
[![Release](https://img.shields.io/github/v/release/Lutiancheng1/gemini-webapi-proxy?include_prereleases)](https://github.com/Lutiancheng1/gemini-webapi-proxy/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Flutiancheng1%2Fgemini--webapi--proxy-blue)](https://ghcr.io/Lutiancheng1/gemini-webapi-proxy)

[English](README.md) · [中文](README.zh.md)

</div>

<p align="center">
  <img src="docs/assets/hero-lemon.png" alt="Lemon watercolor generated through the proxy" width="512">
  <br><em>Generated via <code>POST /openai/v1/images/generations</code> · <code>gemini-2.5-pro-image</code></em>
</p>

---

## 🤔 Why this project?

Google's official Gemini API requires a paid API key with separate quota. **This
proxy is for people who already have a Gemini Web session** (you log in via
browser, free daily quota) and want to use that session from any OpenAI-style
client — without copy-pasting prompts into the web UI.

- **No API key, no payment.** Uses your existing Gemini Web login (Safari
  cookies, env vars, or a cookies.txt).
- **One server, every OpenAI client.** Point OpenAI Python SDK, LobeChat,
  NextChat, ChatBox, or your own scripts at `http://localhost:4982/openai`.
- **Image gen, not just chat.** Returns base64 PNG/JPEG so downstream
  clients don't have to wrestle with Google's CDN redirects.
- **Docker one-liner.** A long-running container with auto-restart and
  cookie refresh via the macOS host's Safari.

> **Disclaimer:** This project is not affiliated with Google. It uses
> [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API), a
> reverse-engineered client of the Gemini Web frontend. Usage is subject
> to Google's Terms of Service. You are responsible for your own usage.

---

## 📑 Table of contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [🔌 Wiring a client](#-wiring-a-client)
- [🖼 Image generation](#-image-generation)
- [⚙️ Configuration](#-configuration)
- [🏗 Architecture](#-architecture)
- [🐳 Deployment & operations](#-deployment--operations)
- [🛣 Roadmap](#-roadmap)
- [🧪 Development](#-development)
- [❓ Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [⚖️ License](#-license)
- [🙏 Acknowledgements](#-acknowledgements)

---

## ✨ Features

- 🪄 **Drop-in OpenAI API** — point any OpenAI client (Python SDK, OpenAI CLI, ChatBox, NextChat, LobeChat, Outsider Studio, …) at `http://localhost:4982/openai`
- 💬 **Chat completions** — non-streaming JSON, multi-turn, reference images
- 🖼 **Image generation** — base64 output only (no CDN URL leakage), text-to-image + reference-image-to-image
- 🍪 **Pluggable cookie sources** — desktop browser (Safari/Chrome/…), env vars, Netscape cookie file
- 🐳 **One-command Docker** — `docker compose up -d`, auto-restart, host network bridge for the local proxy
- 🔌 **Multi-fallback image download** — Playwright Chromium → httpx → curl_cffi → library save
- 🛡 **Upstream refusal detection** — Gemini "I cannot fulfill…" answers mapped to HTTP 403, not 200
- 🛠 **Optional API key** — `GOP_API_KEY=...` enables Bearer auth; empty = off (local-only default)
- 📋 **Curated model list** — advertises a small fixed set of `gemini-3-*` chat and `gemini-2.5-*-image` aliases via `/openai/v1/models`

## 🚀 Quick Start

You need either:

- **A logged-in Gemini Web session** in Safari/Chrome on macOS or Linux, **or**
- A `__Secure-1PSID` / `__Secure-1PSIDTS` pair from `gemini.google.com`, **or**
- A Netscape-format `cookies.txt` exported from a browser.

Pick one install path:

### Option A: `pip` (PyPI)

```bash
pip install "gemini-webapi-proxy[browser-cookie]"
gemini-webapi-proxy            # starts on :4982
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

### Option C: Docker (long-running)

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
bash scripts/docker-up.sh
```

`scripts/docker-up.sh` syncs your browser cookies into `data/runtime.env`
(only needed on macOS — Linux hosts can use env vars directly), then
launches the container.

In all three cases, verify the service:

```bash
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-webapi-proxy"}
```

See [docs/docker.md](docs/docker.md) for the full deployment guide.

## 🔌 Wiring a client

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4982/openai/v1",
    api_key="not-verified",   # any non-empty string; or set GOP_API_KEY
)

resp = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
)
print(resp.choices[0].message.content)
```

Curated chat models: `gemini-3-flash`, `gemini-3-pro`. See what your
deployment advertises with:

```bash
curl -sS http://localhost:4982/openai/v1/models | python3 -m json.tool
```

See [docs/studio.md](docs/studio.md) for connecting OpenAI-compatible
desktop apps, and [docs/api.md](docs/api.md) for the full API reference.

## 🖼 Image generation

```python
import base64, pathlib

img = client.images.generate(
    model="gemini-2.5-pro-image",       # stable alias — see /openai/v1/models
    prompt="a still life watercolor of lemons in a bowl, soft pastel colors",
    n=1,
    response_format="b64_json",
)
pathlib.Path("out.png").write_bytes(base64.b64decode(img.data[0].b64_json))
```

With a reference image:

```python
import base64, pathlib

data_url = (
    "data:image/png;base64,"
    + base64.b64encode(pathlib.Path("ref.png").read_bytes()).decode()
)
img = client.images.generate(
    model="gemini-2.5-pro-image",
    prompt="a portrait in the same style as the reference",
    n=1, size="1024x1024",
    extra_body={"image": [data_url]},
)
pathlib.Path("out.png").write_bytes(base64.b64decode(img.data[0].b64_json))
```

The proxy always returns `b64_json` (never Google CDN URLs) because most
downstream clients can't fetch `lh3.googleusercontent.com/...` directly.
See [docs/api.md](docs/api.md#reference-images) and
[docs/downloaders.md](docs/downloaders.md) for the download chain.

## ⚙️ Configuration

All configuration is via environment variables. The `GOP_` prefix is
recommended; a few unprefixed names (`PORT`, `USE_BROWSER_COOKIES`, …)
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
| `GOP_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |
| `GOP_DATA_DIR` | `./data` | where the model registry file lives |

See [docs/configuration.md](docs/configuration.md) for the full list and
detailed semantics.

## 🏗 Architecture

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
└────────────────────────────────────────────────┘
```

- **Pluggable cookie sources** (`gemini_webapi_proxy.cookies`) — add a new
  one by subclassing `BaseCookieSource` and registering it.
- **Pluggable image downloaders** (`gemini_webapi_proxy.downloaders`) —
  each strategy is a small class; reorder the chain in `GOP_DOWNLOADER_CHAIN`.
- **Pluggable Gemini client** (`gemini_webapi_proxy.client`) — current
  implementation wraps `gemini-webapi`; future backends can implement
  `BaseGeminiClient` without touching the rest of the code.
- **Curated model registry** (`gemini_webapi_proxy.client.registry`) —
  two chat entries (`gemini-3-flash`, `gemini-3-pro`) and two stable
  image aliases (`gemini-2.5-flash-image`, `gemini-2.5-pro-image`).
  The reverse-alias index is guarded so that asking for `gemini-3-pro`
  can never route to an image alias by accident.

See [docs/architecture.md](docs/architecture.md) for the deeper data flow
(cookie bootstrap → registry sync → request → RPC → downloader chain →
b64 response).

## 🐳 Deployment & operations

- **[Docker on macOS](docs/docker.md)** — long-running container with
  `restart: unless-stopped`, syncs Safari cookies via `scripts/docker-up.sh`.
- **[Docker on Linux](docs/docker.md#linux-host)** — set `GOP_GEMINI_1PSID` /
  `GOP_GEMINI_1PSIDTS` in `.env`; no browser cookie source needed.
- **Bare-metal / venv** — `./start.sh` or `python -m gemini_webapi_proxy`.
- **Cookie refresh** — Safari re-login → `python scripts/sync_runtime_env.py`
  → `docker compose restart`. See
  [docs/troubleshooting.md](docs/troubleshooting.md#cookie-cache).

## 🛣 Roadmap

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
bash scripts/e2e-image.sh   # requires a real Gemini session
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contribution workflow,
[docs/architecture.md](docs/architecture.md) for the design, and
[examples/](examples/) for runnable code samples.

## ❓ Troubleshooting

The short version:

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Failed to connect to localhost:4982` | server not started | `bash scripts/docker-up.sh` or `./start.sh` |
| 401 / `AuthError` from upstream | cookie expired | re-login in Safari, re-run `scripts/sync_runtime_env.py`, `docker compose restart` |
| 403 `"I cannot fulfill..."` | upstream safety filter | try a different prompt, or check the model list |
| 502 with `Multiple cookies exist` | `.com` vs `.com.hk` duplicates | already auto-filtered; if not, `docker compose restart` |
| 502 (b64 download) | Playwright missing | `playwright install chromium` (host) or rebuild Docker image |
| Upstream `Unknown model name: gemini-2.5-pro-image` against a `gemini-3-pro` request | fixed in 0.1.0 — re-pull the image and restart | `docker compose pull && docker compose up -d` |

Full troubleshooting matrix: [docs/troubleshooting.md](docs/troubleshooting.md).

## 🤝 Contributing

PRs welcome! Read [CONTRIBUTING.md](CONTRIBUTING.md) for the dev setup,
conventional-commit format, and the release process. Bug reports go to
[GitHub Issues](https://github.com/Lutiancheng1/gemini-webapi-proxy/issues);
security issues go to the address in [SECURITY.md](SECURITY.md), not to
public issues.

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
- All [contributors](https://github.com/Lutiancheng1/gemini-webapi-proxy/graphs/contributors)
  and early testers
