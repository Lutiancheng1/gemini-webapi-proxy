# Build the proxy in two stages so the runtime image stays small.
#
# NOTE: the build expects to be run with `--network=host` (or a working
# egress proxy configured below).  The defaults assume the host has a
# working HTTP/HTTPS proxy on 7897 (Clash etc.) — override
# GOP_BUILD_HTTP_PROXY at build time if yours is elsewhere.

ARG GOP_BUILD_HTTP_PROXY=""

# NOTE: we deliberately use the full `bookworm` image (not `slim`) because
# curl_cffi's prebuilt aarch64 wheel links against OpenSSL 1.1, which the
# slim image does not ship. The slim variant causes "OPENSSL_internal:
# invalid library" errors when calling gemini-webapi's RPC.
FROM python:3.12-bookworm AS builder

ARG GOP_BUILD_HTTP_PROXY

# Reset every proxy-related env var to the build-time value (or empty)
# so apt/pip inside the builder don't inherit anything from the host.
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HTTP_PROXY=${GOP_BUILD_HTTP_PROXY} \
    HTTPS_PROXY=${GOP_BUILD_HTTP_PROXY} \
    http_proxy=${GOP_BUILD_HTTP_PROXY} \
    https_proxy=${GOP_BUILD_HTTP_PROXY} \
    ALL_PROXY=${GOP_BUILD_HTTP_PROXY} \
    all_proxy=${GOP_BUILD_HTTP_PROXY}

WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
# Readme + license are needed by hatchling when building the wheel.
COPY README.md README.zh.md LICENSE NOTICE CHANGELOG.md ./

RUN python -m pip install --upgrade pip build hatchling && \
    python -m build --wheel --outdir /wheels

# ---- Runtime image ------------------------------------------------------
FROM python:3.12-bookworm

ARG GOP_BUILD_HTTP_PROXY

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=4982 \
    GOP_COOKIE_SOURCE=env \
    GOP_PROBE_ON_START=false \
    GOP_LOG_FORMAT=json \
    GOP_LOG_LEVEL=INFO \
    HTTP_PROXY=${GOP_BUILD_HTTP_PROXY} \
    HTTPS_PROXY=${GOP_BUILD_HTTP_PROXY} \
    http_proxy=${GOP_BUILD_HTTP_PROXY} \
    https_proxy=${GOP_BUILD_HTTP_PROXY}

# We need Chromium for the image-download fallback chain.
# Explicitly list the system packages playwright needs (avoids pulling
# `playwright install-deps` which fails on some mirrors).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
        # Chromium runtime dependencies (subset of what `playwright install-deps`
        # would install; keep this list in sync with playwright docs if it grows).
        libnss3 \
        libnspr4 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libpango-1.0-0 \
        libcairo2 \
        libasound2 && \
    rm -rf /var/lib/apt/lists/*

# Pull Playwright's Chromium browser binary (system deps already installed above).
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m pip install --no-cache-dir playwright && \
    playwright install chromium

# Install the application wheel built above.
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

# Persistent data directory.
RUN mkdir -p /app/data
WORKDIR /app
VOLUME ["/app/data"]

EXPOSE 4982

HEALTHCHECK --interval=30s --timeout=8s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4982/health', timeout=5)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "gemini_webapi_proxy", "--host", "0.0.0.0", "--port", "4982"]
