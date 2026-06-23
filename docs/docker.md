# Docker 常驻部署（macOS）

## 为什么用 Docker

- 后台常驻：`restart: unless-stopped`，Docker Desktop 启动后自动拉起
- 端口固定：`4982`，与 Studio `http://localhost:4982/openai` 一致
- 不依赖你手动开终端跑 `./start.sh`

## 限制（必读）

Linux 容器**读不到** macOS Safari Cookie。因此 Docker 模式：

1. 本机脚本 `scripts/sync_runtime_env.py` 从 Safari 读出 `GEMINI_1PSID` / `GEMINI_1PSIDTS`
2. 写入 `data/runtime.env`（已 gitignore）
3. 容器通过 `env_file` 加载，并设 `USE_BROWSER_COOKIES=false`

Cookie 过期后，在本机重新执行同步并 `docker compose restart`。

## 前置条件

| 项 | 要求 |
|----|------|
| Docker Desktop | 已安装并运行 |
| Safari | 已登录 [gemini.google.com](https://gemini.google.com) |
| 本机代理 | Clash 等监听 `7897`（或改 `DOCKER_HTTP_PROXY`） |
| 本机 Python | 3.12 + `.venv`（仅 Cookie 同步脚本需要，首次 `docker-up.sh` 会自动建） |

## 一键启动

```bash
cd gemini-webapi-proxy
bash scripts/docker-up.sh
```

脚本会：

1. 从 Safari 同步 Cookie → `data/runtime.env`
2. 释放 4982 端口
3. `docker compose up -d --build`
4. 等待 `/health` 返回 ok

## 开机自启

两层：

1. **Docker Desktop**：系统设置里勾选 **Start Docker Desktop when you log in**
2. **容器策略**：`docker-compose.yml` 中 `restart: unless-stopped`

登录 Mac 后流程：Docker Desktop 启动 → 引擎就绪 → `gemini-webapi-proxy` 容器自动起来。

> Cookie 不会自动从 Safari 同步进容器。若隔天 401，在本机执行一次 Cookie 同步 + 重启（见下方「日常维护」）。

## 日常维护

```bash
# 刷新 Cookie 并重启（401 / signed out / 出图全失败）
.venv/bin/python scripts/sync_runtime_env.py && docker compose restart

# 查看状态
docker compose ps
curl -sS http://localhost:4982/health

# 看日志
docker compose logs -f --tail=100

# 停止
bash scripts/docker-down.sh

# 完全重建镜像
HTTP_PROXY= HTTPS_PROXY= docker compose build --no-cache
docker compose up -d --force-recreate
```

## 环境变量（Docker）

| 变量 | 容器内典型值 | 说明 |
|------|----------------|------|
| `USE_BROWSER_COOKIES` | `false` | 固定，容器内不读浏览器 |
| `GEMINI_1PSID` / `GEMINI_1PSIDTS` | 来自 `data/runtime.env` | 由同步脚本写入 |
| `HTTP_PROXY` | `http://host.docker.internal:7897` | **勿**写 `127.0.0.1`（那是容器自己） |
| `DOCKER_HTTP_PROXY` | compose 插值用 | 可在项目根 `.env` 覆盖 |
| `PROBE_ON_START` | `false` | 加快启动 |

在 `docker-compose.yml` 同目录创建 `.env` 可覆盖 compose 变量，例如：

```env
DOCKER_HTTP_PROXY=http://host.docker.internal:7897
PORT=4982
```

## 构建注意

本机若设置了 `HTTP_PROXY=http://127.0.0.1:7897`，Docker **构建**阶段可能失败。`docker-up.sh` 构建时已清空代理环境变量；手动构建请：

```bash
HTTP_PROXY= HTTPS_PROXY= docker compose build
```

## 数据卷

`./data` 挂载到容器 `/app/data`，持久化 `model_registry.json` 等。`data/runtime.env` 含敏感 Cookie，勿提交 git。
