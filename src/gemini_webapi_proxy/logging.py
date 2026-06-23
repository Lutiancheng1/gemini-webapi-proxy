"""Logging configuration.

Format:  ``GOP_LOG_FORMAT=json`` (default in containerised deployments) or
         ``console`` (default for local development).
Level:   ``GOP_LOG_LEVEL`` (default ``INFO``).
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, ClassVar

from gemini_webapi_proxy.config import get_settings

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Render a single line of JSON per log record."""

    DEFAULT_KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "name",
            "levelname",
            "message",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Promote the standard ``extra={...}`` keys to the top level.
        for k, v in record.__dict__.items():
            if k in self.DEFAULT_KEYS or k.startswith("_"):
                continue
            if k in {
                "args",
                "msg",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "taskName",
            }:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except TypeError:
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Initialise the root logger.  Idempotent."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    s = get_settings()
    root = logging.getLogger()
    # Remove any pre-existing handlers (uvicorn installs its own).
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stderr)
    if s.log_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )
    root.addHandler(handler)
    root.setLevel(s.log_level.upper())

    # Quiet down very chatty libraries.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _CONFIGURED = True
