# 故障排查与维护

## 快速诊断

```bash
# 1. 进程是否在听 4982
curl -sS http://localhost:4982/health

# 2. Docker 状态
docker compose ps
docker compose logs --tail=50

# 3. 端到端
bash scripts/e2e-image.sh
```

## 常见现象

| 现象 | 原因 | 处理 |
|------|------|------|
| `Failed to connect to localhost:4982` | Proxy 未启动 | `bash scripts/docker-up.sh` 或 `./start.sh` |
| Docker 内 `127.0.0.1:7897` 连不上 | 容器内 127.0.0.1 不是宿主机 | 确认 `HTTP_PROXY=http://host.docker.internal:7897` |
| 401 / signed out / AuthError | Cookie 过期 | Safari 重登 gemini.google.com → `sync_runtime_env.py` → `docker compose restart` |
| 500 并发多张全挂 | Cookie 刷新风暴 | Studio 生图并发改为 1–2；重启 Proxy |
| 502 `Multiple cookies exist with name=NID` / `COMPASS` | 跨域重复 Cookie（.com / .com.hk） | 已内置过滤；仍失败则 `docker compose restart` |
| 502 无法转 b64 | Playwright 下载失败 | Docker 重建镜像；本机 `playwright install chromium` |
| 出图超时 | 默认 300s | 减少并发；检查代理稳定性 |
| `docker ps` 显示 unhealthy 但 health OK | 旧版 healthcheck 用 curl | 更新 `docker-compose.yml` 后 `docker compose up -d --force-recreate` |

## Cookie 缓存

`gemini-webapi` 会在临时目录写 `.cached_cookies_*.json`，陈旧缓存会导致「浏览器仍登录但 API 401」。

本机模式：`session_bootstrap` 启动时会清理（除非 `GEMINI_WEBAPI_KEEP_COOKIE_CACHE=true`）。

手动清理：

```bash
rm -f /var/folders/*/*/T/gemini_webapi/.cached_cookies_*.json
rm -f "$(python3 -c 'import tempfile; print(tempfile.gettempdir())')"/gemini_webapi/.cached_cookies_*.json
```

Docker 模式：重启容器 + 重新 `sync_runtime_env.py`。

## 本机模式 vs Docker

| | `./start.sh` | Docker |
|--|--------------|--------|
| Cookie | 每次请求可读 Safari | 需 `data/runtime.env` 同步 |
| 代理 | `127.0.0.1:7897` | `host.docker.internal:7897` |
| 常驻 | 终端关了就停 | `unless-stopped` |
| 推荐场景 | 临时调试 | 日常给 Studio 用 |

## 开发自测

```bash
.venv/bin/pytest tests/ -q
bash scripts/e2e-image.sh
```
