# Build the proxy in two stages so the runtime image stays small.

ARG GOP_BUILD_HTTP_PROXY=""

# ---- Builder stage: pre-build the wheel so we can install it via
#      pip (handles dependencies properly).  No project code is
#      COPYed from the host here — instead we COPY from the host
#      into a later stage that *only* runs on cache miss, so a
#      code change always invalidates the build.

FROM python:3.12-bookworm AS builder

ARG GOP_BUILD_HTTP_PROXY

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HTTP_PROXY=${GOP_BUILD_HTTP_PROXY} \
    HTTPS_PROXY=${GOP_BUILD_HTTP_PROXY} \
    http_proxy=${GOP_BUILD_HTTP_PROXY} \
    https_proxy=${GOP_BUILD_HTTP_PROXY} \
    ALL_PROXY=${GOP_BUILD_HTTP_PROXY} \
    all_proxy=${GOP_BUILD_HTTP_PROXY}

WORKDIR /build
# Build deps only (hatchling + pip).  The actual project source is
# injected in the runtime stage below so code changes always bust
# the cache.
COPY pyproject.toml ./
RUN python -m pip install --upgrade pip build hatchling

# ---- Runtime image ----
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
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
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

# Install the *-runtime* deps from pyproject.toml directly.  This
# avoids the stale-wheel problem of building a wheel from a cached
# source tree in a separate layer.
COPY pyproject.toml README.md README.zh.md LICENSE NOTICE CHANGELOG.md ./
RUN python -m pip install --no-cache-dir hatchling && \
    python -m pip install --no-cache-dir \
        "fastapi>=0.115" \
        "uvicorn[standard]>=0.32" \
        "pydantic>=2.5" \
        "pydantic-settings>=2.1" \
        "httpx>=0.27" \
        "curl-cffi>=0.7" \
        "playwright>=1.49" \
        "gemini-webapi>=2.0" \
        "python-dotenv>=1.0"

# Install Playwright's Chromium browser binary.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m pip install --no-cache-dir playwright && \
    playwright install chromium

# Install the actual project source LAST so any change to src/ forces
# a re-install of the package without any wheel caching.
COPY src ./src
RUN python -m pip install --no-cache-dir -e . && \
    rm -rf /build /tmp/*.whl

# Persistent data directory.
RUN mkdir -p /app/data
WORKDIR /app
VOLUME ["/app/data"]

EXPOSE 4982

HEALTHCHECK --interval=30s --timeout=8s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4982/health', timeout=5)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "gemini_webapi_proxy", "--host", "0.0.0.0", "--port", "4982"]
