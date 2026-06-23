"""Detect Gemini Web plain-text refusals (policy / capability limits / sign-out).

When the user is signed out of gemini.google.com in the browser the source
cookie jar came from, Gemini Web returns a small set of short refusal strings
instead of the actual answer.  We detect those so the proxy can map them to
HTTP 403 with an actionable error message, rather than letting the client
treat a refusal as a successful response.

If you encounter a new Gemini refusal string that this module does NOT
catch, please add it to the appropriate tuple below.
"""

from __future__ import annotations

# Short refusals emitted specifically by the image-generation pipeline.
_IMAGE_REFUSAL_PHRASES = (
    "can't create",
    "can't seem to create",
    "cannot create",
    "image creation isn't available",
    "image generation isn't available",
    "are you signed in",
    "are you signed out",
    "signed out",
    "isn't available in your location",
    "not available in your location",
    "feature isn't available",
    "no longer available",
    "try again later",
    # New variants seen in 2026-06 (Google reworded the sign-out refusal).
    "don't seem to have access",
    "i don't seem to have access",
    "do not seem to have access",
    "i'm not able to create",
    "i am not able to create",
    "something went wrong, try again",
    "isn't available for your account",
    "no longer supported in your region",
    # Generic retry / sign-out phrasing seen on 2026-06-23 against
    # accounts that have been recently signed out of gemini.google.com.
    # NOTE: the phrases below are intentionally narrow — "something went
    # wrong" alone is too generic (real model output mentions it) so we
    # only match when it appears in a Gemini-style retry wrapper.
    "please try your request again",
    "try your request again",
    "couldn't generate",
    "could not generate",
    "not able to generate",
    "an error occurred while generating",
    "try again in a moment",
)

# Short refusals emitted by the chat pipeline.
_CHAT_REFUSAL_PHRASES = (
    "cannot fulfill",
    "can't fulfill",
    "i cannot fulfill",
    "i can't fulfill",
    "i'm unable to",
    "i am unable to",
    "i can't help",
    "i cannot help",
)


def looks_like_image_refusal(text: str) -> bool:
    """True if ``text`` looks like an image-generation refusal from upstream."""
    blob = text.lower()
    return any(p in blob for p in _IMAGE_REFUSAL_PHRASES)


def looks_like_upstream_refusal(text: str) -> bool:
    """True if Gemini Web text is a refusal, not real model output."""
    blob = text.lower().strip()
    if not blob:
        return False
    if any(p in blob for p in _CHAT_REFUSAL_PHRASES):
        return True
    if any(p in blob for p in _IMAGE_REFUSAL_PHRASES):
        return True
    return (
        "{" not in blob
        and "}" not in blob
        and len(blob) <= 280
        and ("cannot" in blob or "can't" in blob or "unable" in blob)
    )


# Actionable guidance appended to every 403 returned by the proxy.
# Centralised here so we keep one copy of the troubleshooting text.
COOKIE_REAUTH_HINT = (
    "If this is unexpected, sign in to gemini.google.com in the browser the "
    "cookie source is reading from (e.g. Safari), then re-sync cookies via: "
    "`python scripts/sync_runtime_env.py` and restart the proxy. "
    "If the issue persists, Google may be rate-limiting the account or "
    "blocking the network region."
)
