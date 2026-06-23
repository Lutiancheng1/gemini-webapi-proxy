<div align="center">

# 🌐 Gemini OpenAI Proxy

**OpenAI 兼容的 Google Gemini Web API 网关 — 任何 OpenAI 客户端都能直接用。**

[![PyPI](https://img.shields.io/pypi/v/gemini-openai-proxy.svg)](https://pypi.org/project/gemini-openai-proxy/)
[![CI](https://img.shields.io/github/actions/workflow/status/Lutiancheng1/gemini-openai-proxy/ci.yml?branch=main)](https://github.com/Lutiancheng1/gemini-openai-proxy/actions)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/gemini-openai-proxy.svg)](https://pypi.org/project/gemini-openai-proxy/)

[English](README.md) · [中文](README.zh.md)

</div>

---

## ✨ 特性

- 🪄 **即插即用 OpenAI 接口** — 把 `base_url` 指向 `http://localhost:4982/openai` 就能用，兼容 OpenAI Python SDK、`openai` CLI、ChatBox、NextChat、LobeChat、Outsider Studio 等
- 💬 **对话补全** — 非流式 JSON，多轮，支持参考图
- 🖼️ **图像生成** — 仅返回 base64（不下发 Google CDN URL），文生图 / 参考图生图
- 🍪 **可插拔 Cookie 来源** — 桌面浏览器（Safari/Chrome 等）、环境变量、Netscape cookie 文件
- 🐳 **Docker 一键常驻** — `docker compose up -d`，自启，主机代理网络桥接
- 🔌 **多通道兜底下载** — Playwright Chromium / httpx / curl_cffi / 库内 save
- 🛠️ **可选 API Key** — 设 `GOP_API_KEY=...` 开启 Bearer 鉴权；空 = 关（本地默认）
- 📋 **模型注册表** — 自动发现、探测、起别名，对外暴露 `/openai/v1/models`

> **免责声明**：本项目与 Google 无关。底层依赖 [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API)，该库是对 Gemini Web 前端的逆向工程实现。使用本项目受 Google 服务条款约束，后果自负。

## 🚀 快速开始

### 方式 A：`pip`（PyPI）

```bash
pip install "gemini-openai-proxy[browser-cookie]"
gemini-openai-proxy
```

### 方式 B：从源码

```bash
git clone https://github.com/Lutiancheng1/gemini-openai-proxy
cd gemini-openai-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
./start.sh
```

### 方式 C：Docker

```bash
git clone https://github.com/Lutiancheng1/gemini-openai-proxy
cd gemini-openai-proxy
bash scripts/docker-up.sh
```

脚本会把你本机浏览器的 Gemini Cookie 同步到 `data/runtime.env`（仅 macOS 需要；Linux 主机直接用环境变量），然后启动容器。

三种方式都可以用下面的命令验证服务已起：

```bash
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-openai-proxy"}
```

## 🔌 接入客户端

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4982/openai/v1",
    api_key="not-verified",  # 任意非空字符串；或设置 GOP_API_KEY
)

resp = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
)
print(resp.choices[0].message.content)
```

带参考图的生图：

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

接入 OpenAI 兼容桌面客户端的细节见 [docs/studio.md](docs/studio.md)，完整 API 见 [docs/api.md](docs/api.md)。

## ⚙️ 配置

所有配置通过环境变量。建议用 `GOP_` 前缀；同时保留少量无前缀变量（`PORT`、`USE_BROWSER_COOKIES` 等）作为向后兼容。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GOP_PORT` | `4982` | 监听端口 |
| `GOP_HOST` | `0.0.0.0` | 监听地址 |
| `GOP_API_KEY` | _(空)_ | 非空时校验 `Authorization: Bearer <key>` |
| `GOP_COOKIE_SOURCE` | `browser` | `browser` / `env` / `file` |
| `GOP_BROWSER` | `auto` | `auto` / `safari` / `chrome` / `edge` / `brave` / `chromium` |
| `GOP_COOKIE_FILE` | _(空)_ | Netscape 格式 cookies.txt 路径 |
| `GOP_GEMINI_1PSID` | _(空)_ | `__Secure-1PSID` 值（env / file 模式） |
| `GOP_GEMINI_1PSIDTS` | _(空)_ | `__Secure-1PSIDTS` 值 |
| `GOP_GEMINI_COOKIES_RAW` | _(空)_ | `k1=v1; k2=v2` 形式 |
| `GOP_HTTP_PROXY` | _(空)_ | 本机 HTTP 代理（如 `http://127.0.0.1:7897`） |
| `GOP_CHAT_TIMEOUT` | `180` | 秒 |
| `GOP_IMAGE_TIMEOUT` | `300` | 秒 |
| `GOP_INIT_TIMEOUT` | `120` | 秒 |
| `GOP_PROBE_ON_START` | `false` | 启动时探测模型 |
| `GOP_LOG_FORMAT` | `console` | `console`（开发） / `json`（容器） |
| `GOP_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `GOP_DATA_DIR` | `./data` | 模型注册表所在目录 |

完整列表见 [docs/configuration.md](docs/configuration.md)。

## 🏗️ 架构

```
┌─────────────── FastAPI (uvicorn) ───────────────┐
│  /health    /ready                              │
│  /openai/v1/models  /openai/v1/chat/completions │
│  /openai/v1/images/generations  /admin/probe    │
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

- **可插拔 Cookie 来源**（`gemini_openai_proxy.cookies`）—— 继承 `BaseCookieSource` + 注册即可新增
- **可插拔图片下载器**（`gemini_openai_proxy.downloaders`）—— 每个下载器都是一个小类，通过 `GOP_DOWNLOADER_CHAIN` 调整顺序
- **可插拔 Gemini 客户端**（`gemini_openai_proxy.client`）—— 当前实现包了 `gemini-webapi`；未来后端只需实现 `BaseGeminiClient`

## 🛣️ Roadmap

- [ ] **流式对话补全**（SSE）—— 当前 `stream=true` 返回 400
- [ ] **更多 Gemini 后端** —— 官方 Gemini API、第三方代理
- [ ] **更多 Cookie 来源** —— Playwright storage state 导出、Firefox (browser-cookie3)
- [ ] **按模型限流** —— token-bucket per model id
- [ ] **模型注册表热加载** —— watch `data/model_registry.json`
- [ ] **Prometheus `/metrics` 端点**

## 🧪 开发

```bash
git clone https://github.com/Lutiancheng1/gemini-openai-proxy
cd gemini-openai-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
.venv/bin/pytest tests/ -v
.venv/bin/ruff check
.venv/bin/ruff format
.venv/bin/mypy src/
bash scripts/e2e-image.sh   # 需要真实 Gemini 账号
```

完整流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## ⚖️ 协议

本项目采用 **GPL-3.0-or-later** 协议，详见 [LICENSE](LICENSE)。

依赖 [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API) 同为 GPL-3.0。安装运行时依赖即表示同意其协议。

本项目**与 Google 无关**，不提供任何担保。使用须遵守 Google 服务条款。

## 🙏 致谢

- [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) — 上游逆向客户端，没有它就没有这个项目
- OpenAI Python SDK 团队 — 干净、广为实现的 API 协议，让这类网关容易构建
