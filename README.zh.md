<div align="center">

# 🌐 Gemini WebAPI Proxy

**Google Gemini Web 的 OpenAI 兼容反向代理(对话 + 出图)。**
任意 OpenAI 客户端直接换 `base_url` 就能用 —— **无需 API Key,复用浏览器登录态**。

[![PyPI](https://img.shields.io/pypi/v/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![CI](https://img.shields.io/github/actions/workflow/status/Lutiancheng1/gemini-webapi-proxy/ci.yml?branch=main)](https://github.com/Lutiancheng1/gemini-webapi-proxy/actions)
[![Release](https://img.shields.io/github/v/release/Lutiancheng1/gemini-webapi-proxy?include_prereleases)](https://github.com/Lutiancheng1/gemini-webapi-proxy/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/pypi/pyversions/gemini-webapi-proxy.svg)](https://pypi.org/project/gemini-webapi-proxy/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io%2Flutiancheng1%2Fgemini--webapi--proxy-blue)](https://ghcr.io/Lutiancheng1/gemini-webapi-proxy)

[English](README.md) · [中文](README.zh.md)

</div>

<p align="center">
  <img src="docs/assets/hero-lemon.png" alt="通过代理生成的水彩柠檬" width="512">
  <br><em>由 <code>POST /openai/v1/images/generations</code> 调用 <code>gemini-2.5-pro-image</code> 生成</em>
</p>

---

## 🤔 为什么需要这个项目?

Google 官方 Gemini API 需要付费 API Key + 独立配额。**本项目给已经登录
Gemini Web 的人用** —— 浏览器里登录就有免费每日额度,想把这个会话
从任何 OpenAI 风格客户端(脚本、LobeChat、NextChat、Outsider Studio …)用上,
不用反复复制粘贴 prompt 到网页。

- **无需 API Key,无需付费。** 复用你现有的 Gemini Web 登录态
  (Safari Cookie / 环境变量 / cookies.txt)
- **一个服务,所有 OpenAI 客户端通用。** OpenAI Python SDK、LobeChat、
  NextChat、ChatBox 或者你自己的脚本,都指向
  `http://localhost:4982/openai` 就能用
- **出图也能用。** 强制返回 base64 PNG/JPEG,下游客户端不用折腾
  Google CDN 跳转链
- **Docker 一行起。** 长驻容器,自动重启,macOS 主机自动同步 Safari Cookie

> **免责声明**:本项目与 Google 无关。底层依赖
> [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API),该库是
> 对 Gemini Web 前端的逆向工程实现。使用须遵守 Google 服务条款,
> 后果自负。

---

## 📑 目录

- [✨ 特性](#-特性)
- [🚀 快速开始](#-快速开始)
- [🔌 接入客户端](#-接入客户端)
- [🖼 图像生成](#-图像生成)
- [⚙️ 配置](#-配置)
- [🏗 架构](#-架构)
- [🐳 部署与运维](#-部署与运维)
- [🛣 路线图](#-路线图)
- [🧪 开发](#-开发)
- [❓ 故障排查](#-故障排查)
- [🤝 贡献](#-贡献)
- [⚖️ 协议](#-协议)
- [🙏 致谢](#-致谢)

---

## ✨ 特性

- 🪄 **即插即用 OpenAI 接口** — 把 `base_url` 指向 `http://localhost:4982/openai` 就能用,兼容 OpenAI Python SDK、`openai` CLI、ChatBox、NextChat、LobeChat、Outsider Studio 等
- 💬 **对话补全** — 非流式 JSON,多轮,支持参考图
- 🖼 **图像生成** — 仅返回 base64(不下发 Google CDN URL),文生图 / 参考图生图
- 🍪 **可插拔 Cookie 来源** — 桌面浏览器(Safari/Chrome 等)、环境变量、Netscape cookie 文件
- 🐳 **Docker 一键常驻** — `docker compose up -d`,自启,主机代理网络桥接
- 🔌 **多通道兜底下载** — Playwright Chromium → httpx → curl_cffi → 库内 save
- 🛡 **上游拒绝识别** — Gemini "I cannot fulfill…" 之类的回答被映射为 HTTP 403,不会伪装成 200
- 🛠 **可选 API Key** — 设 `GOP_API_KEY=...` 开启 Bearer 鉴权;空 = 关(本地默认)
- 📋 **精选模型列表** — 固定暴露 `gemini-3-*` 对话 + `gemini-2.5-*-image` 出图别名,通过 `/openai/v1/models` 可查

## 🚀 快速开始

你需要满足**任一**条件:

- 在 Safari/Chrome(macOS 或 Linux)上**已登录 Gemini Web**,**或**
- 拿到 `gemini.google.com` 的 `__Secure-1PSID` / `__Secure-1PSIDTS` 一对值,**或**
- 从浏览器导出 Netscape 格式的 `cookies.txt`。

挑一种装法:

### 方式 A:`pip`(PyPI)

```bash
pip install "gemini-webapi-proxy[browser-cookie]"
gemini-webapi-proxy            # 监听 :4982
```

### 方式 B:从源码

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
python3 -m venv .venv
.venv/bin/pip install -e ".[browser-cookie,dev]"
.venv/bin/playwright install chromium
./start.sh
```

### 方式 C:Docker(长驻)

```bash
git clone https://github.com/Lutiancheng1/gemini-webapi-proxy
cd gemini-webapi-proxy
bash scripts/docker-up.sh
```

`scripts/docker-up.sh` 会把浏览器 Cookie 同步到 `data/runtime.env`
(仅 macOS 需要;Linux 直接用环境变量),然后启动容器。

三种方式起好后,验证一下:

```bash
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-webapi-proxy"}
```

完整部署指南见 [docs/docker.md](docs/docker.md)。

## 🔌 接入客户端

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:4982/openai/v1",
    api_key="not-verified",   # 任意非空字符串;或设 GOP_API_KEY
)

resp = client.chat.completions.create(
    model="gemini-3-flash",
    messages=[{"role": "user", "content": "Reply with exactly: pong"}],
)
print(resp.choices[0].message.content)
```

精选对话模型:`gemini-3-flash`、`gemini-3-pro`。可查你的部署实际暴露了哪些:

```bash
curl -sS http://localhost:4982/openai/v1/models | python3 -m json.tool
```

接入 OpenAI 兼容桌面客户端的细节见 [docs/studio.md](docs/studio.md),
完整 API 见 [docs/api.md](docs/api.md)。

## 🖼 图像生成

```python
import base64, pathlib

img = client.images.generate(
    model="gemini-2.5-pro-image",       # 稳定别名 —— 见 /openai/v1/models
    prompt="a still life watercolor of lemons in a bowl, soft pastel colors",
    n=1,
    response_format="b64_json",
)
pathlib.Path("out.png").write_bytes(base64.b64decode(img.data[0].b64_json))
```

带参考图:

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

代理**始终**返回 `b64_json`(永不下发 Google CDN URL),因为大多数下游
客户端无法直连 `lh3.googleusercontent.com/...`。出图流水线与下载链
见 [docs/api.md](docs/api.md#reference-images) 和
[docs/downloaders.md](docs/downloaders.md)。

## ⚙️ 配置

所有配置通过环境变量。建议用 `GOP_` 前缀;同时保留少量无前缀变量
(`PORT`、`USE_BROWSER_COOKIES` 等)作为向后兼容。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GOP_PORT` | `4982` | 监听端口 |
| `GOP_HOST` | `0.0.0.0` | 监听地址 |
| `GOP_API_KEY` | _(空)_ | 非空时校验 `Authorization: Bearer <key>` |
| `GOP_COOKIE_SOURCE` | `browser` | `browser` / `env` / `file` |
| `GOP_BROWSER` | `auto` | `auto` / `safari` / `chrome` / `edge` / `brave` / `chromium` |
| `GOP_COOKIE_FILE` | _(空)_ | Netscape 格式 cookies.txt 路径 |
| `GOP_GEMINI_1PSID` | _(空)_ | `__Secure-1PSID` 值(env / file 模式) |
| `GOP_GEMINI_1PSIDTS` | _(空)_ | `__Secure-1PSIDTS` 值 |
| `GOP_GEMINI_COOKIES_RAW` | _(空)_ | `k1=v1; k2=v2` 形式 |
| `GOP_HTTP_PROXY` | _(空)_ | 本机 HTTP 代理(如 `http://127.0.0.1:7897`) |
| `GOP_CHAT_TIMEOUT` | `180` | 秒 |
| `GOP_IMAGE_TIMEOUT` | `300` | 秒 |
| `GOP_INIT_TIMEOUT` | `120` | 秒 |
| `GOP_PROBE_ON_START` | `false` | 启动时探测模型 |
| `GOP_LOG_FORMAT` | `console` | `console`(开发)/ `json`(容器) |
| `GOP_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `GOP_DATA_DIR` | `./data` | 模型注册表所在目录 |

完整列表见 [docs/configuration.md](docs/configuration.md)。

## 🏗 架构

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

- **可插拔 Cookie 来源**(`gemini_webapi_proxy.cookies`) —— 继承
  `BaseCookieSource` + 注册即可新增
- **可插拔图片下载器**(`gemini_webapi_proxy.downloaders`) —— 每个下载器
  都是一个小类,通过 `GOP_DOWNLOADER_CHAIN` 调整顺序
- **可插拔 Gemini 客户端**(`gemini_webapi_proxy.client`) —— 当前实现包了
  `gemini-webapi`;未来后端只需实现 `BaseGeminiClient`
- **精选模型注册表**(`gemini_webapi_proxy.client.registry`) —— 固定
  暴露 2 个对话(`gemini-3-flash`、`gemini-3-pro`)和 2 个出图别名
  (`gemini-2.5-flash-image`、`gemini-2.5-pro-image`)。反向别名索引加了
  守卫,避免请求 `gemini-3-pro` 时被图像别名意外吞掉。

完整数据流(cookie 引导 → registry sync → 请求 → RPC → 下载链 → b64
响应)见 [docs/architecture.md](docs/architecture.md)。

## 🐳 部署与运维

- **[macOS Docker](docs/docker.md)** —— 长驻容器,`restart: unless-stopped`,
  通过 `scripts/docker-up.sh` 同步 Safari Cookie
- **[Linux Docker](docs/docker.md#linux-host)** —— 在 `.env` 里设
  `GOP_GEMINI_1PSID` / `GOP_GEMINI_1PSIDTS`;不需要 browser cookie source
- **裸机 / venv** —— `./start.sh` 或 `python -m gemini_webapi_proxy`
- **Cookie 刷新** —— Safari 重新登录 → `python scripts/sync_runtime_env.py`
  → `docker compose restart`。详见
  [docs/troubleshooting.md](docs/troubleshooting.md#cookie-cache)

## 🛣 路线图

- [ ] **流式对话补全**(SSE) —— 当前 `stream=true` 返回 400
- [ ] **更多 Gemini 后端** —— 官方 Gemini API、第三方代理
- [ ] **更多 Cookie 来源** —— Playwright storage state 导出、Firefox (browser-cookie3)
- [ ] **按模型限流** —— token-bucket per model id
- [ ] **模型注册表热加载** —— watch `data/model_registry.json`
- [ ] **Prometheus `/metrics` 端点**

## 🧪 开发

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
bash scripts/e2e-image.sh   # 需要真实 Gemini 账号
```

完整流程见 [CONTRIBUTING.md](CONTRIBUTING.md),设计见
[docs/architecture.md](docs/architecture.md),可运行示例见
[examples/](examples/)。

## ❓ 故障排查

速查表:

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `Failed to connect to localhost:4982` | 服务没起 | `bash scripts/docker-up.sh` 或 `./start.sh` |
| 401 / `AuthError` | Cookie 过期 | Safari 重登 gemini.google.com → `scripts/sync_runtime_env.py` → `docker compose restart` |
| 403 `"I cannot fulfill..."` | 上游安全策略 | 换 prompt,或换模型 |
| 502 `Multiple cookies exist` | `.com` vs `.com.hk` 重复 | 已内置过滤;若仍出现 `docker compose restart` |
| 502(b64 下载) | Playwright 缺失 | 本机 `playwright install chromium`;容器内 `docker compose build --no-cache` |
| 上游报 `Unknown model name: gemini-2.5-pro-image`(请求的是 `gemini-3-pro`) | 0.1.0 已修 | `docker compose pull && docker compose up -d` |

完整故障表见 [docs/troubleshooting.md](docs/troubleshooting.md)。

## 🤝 贡献

PR 欢迎!开发流程、conventional commit 格式、发版流程见
[CONTRIBUTING.md](CONTRIBUTING.md)。Bug 报告发
[GitHub Issues](https://github.com/Lutiancheng1/gemini-webapi-proxy/issues);
安全问题请按 [SECURITY.md](SECURITY.md) 里的地址发邮件,不要在公开 issue
里贴。

## ⚖️ 协议

本项目采用 **GPL-3.0-or-later** 协议,详见 [LICENSE](LICENSE)。

依赖 [`gemini-webapi`](https://github.com/HanaokaYuzu/Gemini-API) 同为
GPL-3.0。安装运行时依赖即表示同意其协议。

本项目**与 Google 无关**,不提供任何担保。使用须遵守 Google 服务条款。

## 🙏 致谢

- [HanaokaYuzu/Gemini-API](https://github.com/HanaokaYuzu/Gemini-API) ——
  上游逆向客户端,没有它就没有这个项目
- OpenAI Python SDK 团队 —— 干净、广为实现的 API 协议,让这类网关
  容易构建
- 所有 [contributors](https://github.com/Lutiancheng1/gemini-webapi-proxy/graphs/contributors)
  和早期测试者
