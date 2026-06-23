#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://localhost:4982/openai}"
HEALTH="${HEALTH:-http://localhost:4982/health}"
OUT="${OUT:-/tmp/gemini-proxy-e2e-apple.png}"

echo "== health =="
curl -sS "$HEALTH" | tee /dev/stderr | grep -q ok

echo "== chat =="
CHAT=$(curl -sS -m 120 -X POST "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer test" -H "Content-Type: application/json" \
  -d '{"model":"gemini-3-flash","messages":[{"role":"user","content":"Reply with exactly: pong"}],"stream":false}')
echo "$CHAT" | python3 -c "import json,sys; j=json.load(sys.stdin); assert 'error' not in j, j['error']; print(j['choices'][0]['message']['content'])"

echo "== image =="
curl -sS -m 300 -X POST "$BASE/v1/images/generations" \
  -H "Authorization: Bearer test" -H "Content-Type: application/json" \
  -d '{"model":"gemini-3-flash","prompt":"a simple red apple on white background, product photo","n":1,"size":"1024x1024"}' \
  -o /tmp/gemini-proxy-e2e.json -w "HTTP:%{http_code}\n"

python3 <<PY
import base64, json, sys
from pathlib import Path
j = json.loads(Path("/tmp/gemini-proxy-e2e.json").read_text())
if "error" in j:
    print(j["error"].get("message", j["error"])[:800], file=sys.stderr)
    sys.exit(1)
d = j["data"][0]
assert not d.get("url"), "proxy must not expose CDN url"
b64 = d.get("b64_json") or ""
assert b64, "missing b64_json"
raw = base64.b64decode(b64)
Path("$OUT").write_bytes(raw)
ok = raw.startswith(b"\\x89PNG") or raw.startswith(b"\\xff\\xd8\\xff") or (raw[:4]==b"RIFF" and raw[8:12]==b"WEBP")
print("bytes", len(raw), "magic_ok", ok, "saved", "$OUT")
assert len(raw) > 1024 and ok
print("E2E PASS")
PY
