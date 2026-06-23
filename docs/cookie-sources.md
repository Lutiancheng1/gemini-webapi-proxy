# Cookie Sources

The proxy can read Gemini Web cookies from three sources. Pick one with
`GOP_COOKIE_SOURCE`.

| Source | `GOP_COOKIE_SOURCE` | Best for | Cookie refresh |
|--------|---------------------|----------|----------------|
| Desktop browser | `browser` | Local development on macOS / desktop Linux | Automatic on every request |
| Environment variables | `env` | Docker, headless servers, CI | Manual (re-export + restart) |
| Netscape cookie file | `file` | Headless servers without browser access | Manual (re-export + reload) |

## `browser` (default on desktop)

Uses [`browser-cookie3`](https://github.com/borisbabic/browser_cookie3)
to read `google.com` cookies from a real browser. Order of preference:

* macOS: Safari, Chrome, Edge, Brave, Chromium
* Linux / Windows: Chrome, Edge, Brave, Chromium, Safari

Pick a specific browser with `GOP_BROWSER=safari|chrome|edge|brave|chromium`.

```bash
# macOS — first time only
pip install "gemini-webapi-proxy[browser-cookie]"
.venv/bin/playwright install chromium   # only if you'll generate images
./start.sh
```

The first request to the proxy will read the cookies, call
`gemini-webapi.init()`, and on subsequent requests the client stays in
memory. If the cookies go stale, the proxy auto-invalidates its client
and the next request re-reads the browser.

## `env` (recommended for Docker)

Set the cookie values directly:

```bash
export GOP_COOKIE_SOURCE=env
export GOP_GEMINI_1PSID='paste from DevTools'
export GOP_GEMINI_1PSIDTS='paste from DevTools'
export GOP_HTTP_PROXY='http://host.docker.internal:7897'
./start.sh
```

To obtain the values:

1. Open [gemini.google.com](https://gemini.google.com) in a logged-in
   browser tab.
2. DevTools → Application → Cookies → `https://gemini.google.com`.
3. Copy the values of `__Secure-1PSID` and `__Secure-1PSIDTS`.

Or use the helper script (macOS hosts only):

```bash
python scripts/sync_runtime_env.py --browser safari
# writes data/runtime.env (chmod 600) with GOP_GEMINI_1PSID/PSIDTS/PROXY
```

## `file`

Useful for headless Linux servers that don't have a desktop browser and
where you don't want to hand-edit env files.

```bash
# 1. On any machine that has a browser session:
#    install "Get cookies.txt LOCALLY" extension,
#    export cookies for google.com → save as cookies.txt
# 2. SCP / copy cookies.txt to the server
# 3. Set:
export GOP_COOKIE_SOURCE=file
export GOP_COOKIE_FILE=/etc/gemini-webapi-proxy/cookies.txt
./start.sh
```

Expected file format (Netscape, the same one `curl` uses):

```
# Netscape HTTP Cookie File
.google.com	TRUE	/	TRUE	9999999999	__Secure-1PSID	abc123
.google.com	TRUE	/	TRUE	9999999999	__Secure-1PSIDTS	xyz789
```

The `HttpOnly_` prefix is tolerated (some exporters add it).
