# 04 — Connect Outsider Studio (the GUI client)

Outsider Studio is a desktop chat app that supports any **custom OpenAI
base URL**. Point it at the proxy and you get a polished chat +
image-generation UI on top of your Gemini Web session — no copy-paste.

## 1. Start the proxy

```bash
# one-time, on the host that will run Studio
bash scripts/docker-up.sh
curl -sS http://localhost:4982/health
# {"status":"ok","service":"gemini-webapi-proxy"}
```

## 2. Open Outsider Studio

In the **Provider** / **Custom OpenAI** settings:

| Field | Value |
|-------|-------|
| Base URL | `http://localhost:4982/openai` |
| API Key | `not-verified` (any non-empty string; or your real `GOP_API_KEY` if you set one) |
| Chat model | `gemini-3-flash` (or `gemini-3-pro` if you want the bigger model) |
| Image model | `gemini-2.5-flash-image` (stable alias) |
| Image concurrency | `1` (see [docs/troubleshooting.md](../docs/troubleshooting.md)) |

> **Important:** the Base URL **must end with `/openai`**. Studio
> appends `/v1/chat/completions` and `/v1/images/generations`
> automatically. If you put `/openai/v1` you'll get 404s.

## 3. Verify

In Studio, send "Reply with exactly: pong". You should get
`pong` back from `gemini-3-flash`.

If the request fails:

- **401** — your Safari session expired. Re-login in Safari, then
  `python scripts/sync_runtime_env.py && docker compose restart`.
- **403 "I cannot fulfill…"** — Gemini's safety filter; try a different
  prompt.
- **404** — check the Base URL; it must end with `/openai` (no
  trailing `/v1`).
- **Studio's image model picker is empty** — call
  `curl -sS http://localhost:4982/openai/v1/models` and confirm the
  four expected ids are listed. If not, see
  [docs/architecture.md](../docs/architecture.md#the-curated-registry).
