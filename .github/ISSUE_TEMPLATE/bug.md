---
name: Bug Report
about: Something isn't working as expected
title: "bug: "
labels: ["bug"]
assignees: []
---

## What happened

<!-- A clear, one-paragraph description of the bug. -->

## How to reproduce

```bash
# Exact commands and configuration you used.
# Include the relevant GOP_* env vars (NEVER paste real cookies).
export GOP_COOKIE_SOURCE=env
export GOP_GEMINI_1PSID=REDACTED
...
curl -sS -X POST http://localhost:4982/openai/v1/...
```

## Expected behaviour

<!-- What you expected to happen. -->

## Actual behaviour

<!-- What actually happened. Paste the full error / response. -->

```text
Paste error / response here.
```

## Environment

- gemini-webapi-proxy version (`pip show gemini-webapi-proxy` or `git rev-parse HEAD`)
- Python version (`python --version`)
- OS (e.g. macOS 15.4, Ubuntu 24.04, Docker)
- Browser used (if `GOP_COOKIE_SOURCE=browser`)
- Output of `curl -sS http://localhost:4982/health`
- Relevant log lines (`GOP_LOG_LEVEL=DEBUG docker compose logs`, etc.)

## Anything else?

<!-- Screenshots, links to similar issues, workarounds you tried, … -->
