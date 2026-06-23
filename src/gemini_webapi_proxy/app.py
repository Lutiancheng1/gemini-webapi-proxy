"""FastAPI application factory.

Entry point: ``uvicorn gemini_webapi_proxy.app:app``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from gemini_webapi_proxy import __version__
from gemini_webapi_proxy.client.pool import lifespan
from gemini_webapi_proxy.logging import configure_logging
from gemini_webapi_proxy.routes import admin, chat, health, images, models

# Initialise logging before anything else gets a chance to log.
configure_logging()
logger = logging.getLogger(__name__)

# Module-level ``app`` for uvicorn's ``--factory`` and default ``app:app`` lookups.
app = FastAPI(
    title="Gemini WebAPI Proxy",
    description=(
        "OpenAI-compatible API gateway for Google Gemini Web, "
        f"powered by gemini-webapi. v{__version__}"
    ),
    version=__version__,
    lifespan=lifespan,
)
logger.info("gemini-webapi-proxy v%s initialised", __version__)

# Mount routers. Order does not matter.
for r in (health.router, models.router, chat.router, images.router, admin.router):
    app.include_router(r)


def create_app() -> FastAPI:
    """Factory alternative to the module-level ``app`` (for tests)."""
    return app
