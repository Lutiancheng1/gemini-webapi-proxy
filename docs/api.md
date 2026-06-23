# OpenAI 兼容 API

Base：`http://localhost:4982`（Studio 使用 `http://localhost:4982/openai` 作为 OpenAI Base URL）

鉴权：Header `Authorization: Bearer <任意>`（不校验）

## 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 存活检查 |
| GET | `/openai/v1/models` | 模型列表 |
| POST | `/openai/v1/chat/completions` | 对话（`stream=false`） |
| POST | `/openai/v1/images/generations` | 文生图 / 参考图生图 |
| POST | `/admin/probe-models` | 重新探测并刷新模型注册表 |

## 对话示例

```bash
curl -sS -X POST http://localhost:4982/openai/v1/chat/completions \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "messages": [{"role": "user", "content": "Reply with exactly: pong"}],
    "stream": false
  }'
```

## 生图示例

```bash
curl -sS -m 300 -X POST http://localhost:4982/openai/v1/images/generations \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3-flash",
    "prompt": "a simple red apple on white background",
    "n": 1,
    "size": "1024x1024"
  }'
```

响应 `data[0].b64_json` 为 PNG/JPEG base64；`url` 字段不应出现。

## 错误响应

所有错误都遵循 OpenAI 风格：

```json
{"error": {"message": "...", "type": "api_error"}}
```

| HTTP | 含义 | 触发条件 |
|------|------|----------|
| 400 | 客户端错误 | `stream=true` 暂未实现（请设 `false`） |
| 401 | Cookie 失效 | Safari 重新登录 `gemini.google.com` → 重新 sync Cookie |
| 403 | **上游拒绝** | Gemini Web 返回了策略/能力限制文案（"I cannot fulfill…", "image creation isn't available in your location" 等），而非真实答案 |
| 500 | 内部错误 | 兜底；通常是上面分类没覆盖到 |
| 502 | 出图下载失败 | Google CDN 跳链全部失败；查看 `docker compose logs` |
| 504 | 超时 | 默认 `GOP_CHAT_TIMEOUT=180s` / `GOP_IMAGE_TIMEOUT=300s` |

## 参考图

请求体可增加 OpenAI 扩展字段 `image`（字符串或字符串数组），值为 `data:image/png;base64,...`。

Proxy 提示词包装（有参考图时）：

```text
Use the attached reference image(s) as visual reference ...
Prompt: <用户 prompt>
Requested size/aspect: <size>
```

## 出图流水线（内部）

```
POST /images/generations
  → gemini-webapi generate_content（Cookie + 可选 files=参考图）
  → RPC 全尺寸 URL
  → CDN 跳转链
  → Playwright Chromium GET（下载 PNG）
  → b64_json 返回
```

CDN 域名直连，不走 `HTTP_PROXY`（避免 MITM 403）。
