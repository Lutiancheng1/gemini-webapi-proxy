"""Optional API-key authentication.

The proxy is designed for local single-user use and verifies no token by
default.  Set ``GOP_API_KEY`` (non-empty) to require a Bearer token on
every non-health endpoint.  When unset, this module is a pass-through.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from gemini_openai_proxy.config import get_settings


def require_api_key_if_configured(request: Request) -> None:
    """Reject requests without a matching Bearer token when ``GOP_API_KEY`` is set."""
    expected = get_settings().api_key
    if not expected:
        return

    auth = request.headers.get("Authorization") or ""
    scheme, param = get_authorization_scheme_param(auth)
    if scheme.lower() != "bearer" or not param:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (expected: Bearer <GOP_API_KEY>)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if param != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
