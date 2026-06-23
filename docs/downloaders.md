# Image Downloaders

A single Gemini-generated image has to be turned into raw bytes before
the proxy can `base64`-encode it for the OpenAI client. The proxy tries
multiple strategies in order, and the first one to return non-empty
bytes wins.

This is necessary because Google's CDN (the `gg-dl` / `lh3.googleusercontent.com`
chain) is picky: some hops return 403 to plain HTTP clients, some
require a real browser TLS fingerprint, some require a session that has
been "warmed" by visiting `gemini.google.com` first.

## Default chain

```
GOP_DOWNLOADER_CHAIN=playwright-rpc,playwright-preview,httpx-rpc,httpx-preview,library-save
```

| Strategy | Starts from | Transport | Why it's in the chain |
|----------|-------------|-----------|-----------------------|
| `playwright-rpc` | RPC full-size URL | Chromium request context | Most reliable on gg-dl/lh3; matches what Google expects. |
| `playwright-preview` | preview `image.url` | Chromium request context | Fallback when the RPC URL is missing cid/rid. |
| `httpx-rpc` | RPC full-size URL | httpx | Lighter weight; sometimes works where Playwright doesn't. |
| `httpx-preview` | preview `image.url` | httpx | Same, for the preview URL. |
| `library-save` | `image.save()` | gemini-webapi's own downloader | Last resort; uses the library's proven code path. |

## Configuring

Reorder, enable, or disable strategies by editing the chain:

```bash
# Disable Playwright (no Chromium install required)
export GOP_DOWNLOADER_CHAIN='httpx-rpc,httpx-preview,library-save'

# Only the library path (cheapest, lowest success rate)
export GOP_DOWNLOADER_CHAIN='library-save'
```

Each strategy has a per-call timeout (`GOP_DOWNLOADER_TIMEOUT`,
default `120`s). The first strategy that returns within the timeout
wins; later strategies only run if the earlier one returned `None`.

## Adding a new strategy

Subclass `BaseDownloader` in `src/gemini_webapi_proxy/downloaders/`:

```python
from gemini_webapi_proxy.downloaders.base import BaseDownloader, register_downloader

@register_downloader
class MyDownloader(BaseDownloader):
    name = "my-strategy"
    priority = 50  # higher numbers run later

    async def try_download(self, image, *, cookies, settings, client):
        # Return bytes on success, None to fall through,
        # or raise ImageExportError to abort.
        return None
```

Then enable it in the chain:

```bash
export GOP_DOWNLOADER_CHAIN='playwright-rpc,my-strategy,httpx-rpc,...'
```

## Why not just `curl` Google CDN directly?

The redirect chain is:

```
client → gemini.google.com (RPC) → gg-dl/<token>
       → lh3.googleusercontent.com/<id>=d-I?alr=yes
       → lh3.googleusercontent.com/<id>=s2048-rj (final image)
```

Hops 1 and 2 require:

1. A valid `__Secure-1PSID` cookie (we have it)
2. A Referer header from `gemini.google.com` (we send it)
3. A User-Agent and TLS fingerprint that look like a real browser
   (Playwright / curl_cffi handle this; raw `requests` and `httpx`
   often get 403)

The proxy shields downstream clients from this complexity by always
returning base64-encoded bytes.
