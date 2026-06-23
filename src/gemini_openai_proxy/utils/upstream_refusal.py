"""Detect Gemini Web plain-text refusals (policy / capability limits)."""

from __future__ import annotations

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
)

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
    blob = text.lower()
    return any(p in blob for p in _IMAGE_REFUSAL_PHRASES)


def looks_like_upstream_refusal(text: str) -> bool:
    """Return True if Gemini Web text is a refusal, not real model output."""
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
