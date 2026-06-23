"""CLI entry point: ``python -m gemini_openai_proxy`` or ``gemini-openai-proxy``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gemini-openai-proxy",
        description="OpenAI-compatible API gateway for Google Gemini Web.",
    )
    p.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="bind host")
    p.add_argument("--port", type=int, default=int(os.getenv("PORT", "4982")), help="bind port")
    p.add_argument(
        "--reload",
        action="store_true",
        default=os.getenv("RELOAD", "").lower() in {"1", "true", "yes"},
        help="enable auto-reload (development only)",
    )
    p.add_argument(
        "--log-level",
        default=os.getenv("GOP_LOG_LEVEL", os.getenv("LOG_LEVEL", "INFO")),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required: pip install 'uvicorn[standard]'", file=sys.stderr)
        return 2
    uvicorn.run(
        "gemini_openai_proxy.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
