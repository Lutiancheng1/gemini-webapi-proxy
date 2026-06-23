#!/usr/bin/env bash
# Bring up the proxy as a long-running container.
#
# 1. (macOS host only) sync Safari/Chrome cookies → data/runtime.env
# 2. stop any container already on GOP_PORT (default 4982)
# 3. docker compose build + up -d
#    - The build needs GOP_BUILD_HTTP_PROXY set so apt + pip can reach
#      mirrors via the host's local proxy.  Defaults to GOP_HTTP_PROXY
#      (which the user already sets for runtime), or 127.0.0.1:7897.
# 4. wait for /health to return ok
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[browser-cookie,dev]"
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export GOP_PORT="${GOP_PORT:-4982}"
export GOP_BROWSER="${GOP_BROWSER:-safari}"
export GOP_HTTP_PROXY="${GOP_HTTP_PROXY:-http://127.0.0.1:7897}"
# Used by the Dockerfile to talk to apt/pip during `docker build`.  Defaults
# to GOP_HTTP_PROXY; override with GOP_BUILD_HTTP_PROXY if your build
# network is different (e.g. CI without a local proxy).
export GOP_BUILD_HTTP_PROXY="${GOP_BUILD_HTTP_PROXY:-${GOP_HTTP_PROXY}}"

# Only sync browser cookies on macOS (the only platform where it works).
if [[ "$(uname -s)" == "Darwin" ]]; then
  echo "== Sync ${GOP_BROWSER} cookies → data/runtime.env =="
  .venv/bin/python scripts/sync_runtime_env.py --browser "${GOP_BROWSER}"
fi

echo "== Stop anything on :${GOP_PORT} =="
lsof -ti ":${GOP_PORT}" | xargs kill -9 2>/dev/null || true
sleep 1

echo "== Build & start (restart: unless-stopped, host network) =="
GOP_PORT="${GOP_PORT}" \
GOP_BUILD_HTTP_PROXY="${GOP_BUILD_HTTP_PROXY}" \
GOP_HTTP_PROXY="${GOP_HTTP_PROXY}" \
HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= \
  docker compose up -d --build

echo "== Waiting for /health =="
for _ in $(seq 1 40); do
  if curl -fsS "http://localhost:${GOP_PORT}/health" 2>/dev/null | grep -q ok; then
    echo "OK  http://localhost:${GOP_PORT}/health"
    docker compose ps
    exit 0
  fi
  sleep 3
done

echo "Health check timed out — recent logs:" >&2
docker compose logs --tail=80 >&2
exit 1
