#!/usr/bin/env bash
# Start gemini-webapi-proxy from a local venv.
#
# Usage:
#   ./start.sh                 # uses ./.env if present
#   PORT=4983 ./start.sh       # override port
#
# A venv is created on first run at ./.venv (Python 3.10+).
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export PORT="${PORT:-4982}"
export HTTP_PROXY="${HTTP_PROXY:-}"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -e ".[browser-cookie]"
  .venv/bin/playwright install chromium
fi

exec .venv/bin/gemini-webapi-proxy --host 0.0.0.0 --port "$PORT"
