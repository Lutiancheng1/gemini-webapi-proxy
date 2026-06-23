from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from gemini_webapi.types import AvailableModel

from gemini_webapi_proxy.config import REGISTRY_PATH

IMAGE_HINTS = ("image", "imagen", "nano banana", "出图", "图片")
TEXT_BLOCKLIST = ("tts", "audio", "music", "video")


@dataclass
class ModelEntry:
    id: str
    display_name: str
    description: str
    kind: str  # chat | image | both
    chat_ok: bool = False
    image_ok: bool = False
    probed_at: int | None = None
    aliases: list[str] = field(default_factory=list)

    def to_openai(self, created: int, *, image_overrides: set[str] | None = None) -> dict[str, Any]:
        image = self.image_ok or self.kind in {"image", "both"}
        if image_overrides is not None:
            image = image or self.id in image_overrides
        return {
            "id": self.id,
            "object": "model",
            "created": created,
            "owned_by": "google",
            "capabilities": {
                "chat": self.chat_ok or self.kind in {"chat", "both"},
                "image": image,
            },
        }


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-")


# Image-capable model hints.  A model is considered image-capable if its
# name contains any of these (case-insensitive substring match).
_IMAGE_NAME_HINTS = (
    "image",
    "imagen",
    "nano-banana",
    "nano_banana",
    "画图",
    "出图",
    "图片",
)


def is_image_capable_name(model_id: str, image_overrides: set[str] | None = None) -> bool:
    """True if the model id is a known image-generation model.

    Match sources (in priority order):
      1. Explicit override set (GOP_IMAGE_MODELS) — most authoritative
      2. Static name hints (image / imagen / nano-banana / etc.)
    """
    if image_overrides and model_id in image_overrides:
        return True
    lowered = model_id.lower()
    return any(h in lowered for h in _IMAGE_NAME_HINTS)


def _guess_kind(model_name: str, description: str) -> str:
    blob = f"{model_name} {description}".lower()
    if any(x in blob for x in TEXT_BLOCKLIST):
        return "chat"
    has_image = any(x in blob for x in _IMAGE_NAME_HINTS)
    if has_image and "flash" in blob:
        return "image"
    if has_image:
        return "image"
    if "thinking" in blob:
        return "chat"
    return "chat"


def _alias_candidates(model_name: str, description: str) -> list[str]:
    aliases: set[str] = {model_name}
    blob = f"{model_name} {description}".lower()
    if "gemini-3-flash" in model_name and "image" not in blob:
        aliases.add("gemini-3-flash-preview")
    if "gemini-3-pro" in model_name and "image" not in blob:
        aliases.add("gemini-advanced")
        aliases.add("gemini-3-pro-preview")
    if "image" in blob:
        aliases.add(model_name.replace("_", "-"))
        if "2.5" not in model_name:
            aliases.add("gemini-2.5-flash-image")
        aliases.add("gemini-3-pro-image-preview")
        aliases.add("gemini-3.1-flash-image-preview")
    if "2.0-flash" in blob or model_name.endswith("flash"):
        aliases.add("gemini-2.0-flash")
        aliases.add("gemini-2.5-flash")
    return sorted(aliases - {model_name})


class ModelRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, ModelEntry] = {}
        self._alias_index: dict[str, str] = {}
        self._runtime: dict[str, AvailableModel] = {}
        self._loaded = False

    @property
    def entries(self) -> list[ModelEntry]:
        return list(self._entries.values())

    def load_file(self, path: Path = REGISTRY_PATH) -> None:
        if not path.exists():
            self._ensure_image_aliases()
            self._rebuild_aliases()
            return
        raw = json.loads(path.read_text())
        for item in raw.get("models", []):
            entry = ModelEntry(**item)
            self._entries[entry.id] = entry
        self._ensure_image_aliases()
        self._rebuild_aliases()
        self._loaded = bool(self._entries)

    def save_file(self, path: Path = REGISTRY_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": int(time.time()),
            "models": [asdict(e) for e in self._entries.values()],
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def sync_from_client(self, models: list[AvailableModel] | None) -> None:
        if not models:
            return
        self._runtime.clear()
        for m in models:
            if not m.is_available or not (m.model_name or "").strip():
                continue
            self._runtime[m.model_name] = m
            kind = _guess_kind(m.model_name, m.description)
            prev = self._entries.get(m.model_name)
            self._entries[m.model_name] = ModelEntry(
                id=m.model_name,
                display_name=m.display_name or m.model_name,
                description=m.description or "",
                kind=prev.kind if prev else kind,
                chat_ok=prev.chat_ok if prev else kind in {"chat", "both"},
                image_ok=prev.image_ok if prev else kind == "image",
                probed_at=prev.probed_at if prev else None,
                aliases=_alias_candidates(m.model_name, m.description),
            )
        self._ensure_image_aliases()
        self._rebuild_aliases()
        self._loaded = True

    def _rebuild_aliases(self) -> None:
        self._alias_index.clear()
        for entry in self._entries.values():
            self._alias_index[_slug(entry.id)] = entry.id
            for alias in entry.aliases:
                self._alias_index[_slug(alias)] = entry.id

    # ---- Stable image-model aliases ----------------------------------------
    #
    # gemini-webapi 2.0 surfaces the underlying Gemini Web frontend model
    # names (gemini-3-flash, gemini-3-pro).  These don't tell a client
    # *which* model is the image-generation one, and Google has been
    # known to flip them off (`is_available=False`) without notice.
    #
    # We publish two stable aliases — gemini-2.5-flash-image and
    # gemini-2.5-pro-image — that clients can use to mean "the Flash /
    # Pro image-generation model currently in use".  The internal
    # targets (gemini-3-flash, gemini-3-pro) are chosen from whatever
    # is currently available, so the alias stays usable even if one
    # of the underlying models is offline.

    _IMAGE_ALIASES: tuple[tuple[str, str, str], ...] = (
        # (alias_id, target_id, human_name)
        ("gemini-2.5-flash-image", "gemini-3-flash", "Gemini 2.5 Flash Image (nano-banana)"),
        # The pro image alias is kept so resolve_id() still routes
        # 'gemini-2.5-pro-image' to 'gemini-3-pro' for clients that
        # try it, but list_openai_models() no longer advertises it
        # because on most accounts gemini-3-pro is currently rejected
        # by Google's image-generation pipeline.
        ("gemini-2.5-pro-image", "gemini-3-pro", "Gemini 2.5 Pro Image (nano-banana-pro)"),
    )

    _IMAGE_ALIAS_IDS: frozenset[str] = frozenset(a for a, _, _ in _IMAGE_ALIASES)

    def _ensure_image_aliases(self) -> None:
        """Make sure the two stable image-model aliases exist as entries.

        The alias's ``kind`` and ``image_ok`` are always set so clients
        can rely on the capability flag.  We never *override* an
        alias's id or target — the target is fixed so chat calls
        that ask for the alias are routed to the right backend.
        """
        for alias_id, target_id, human_name in self._IMAGE_ALIASES:
            entry = self._entries.get(alias_id)
            if entry is None:
                self._entries[alias_id] = ModelEntry(
                    id=alias_id,
                    display_name=human_name,
                    description=(
                        "Stable alias for the Flash-tier image-generation model. "
                        "Routes internally to "
                        f"{target_id} (Google's nano-banana)."
                    ),
                    kind="image",
                    chat_ok=False,
                    image_ok=True,
                    probed_at=int(time.time()),
                    aliases=[target_id],
                )
            else:
                # Keep the alias's image flag; preserve any chat_ok the
                # user set manually.
                entry.image_ok = True
                entry.kind = "image" if not entry.chat_ok else "both"
                if target_id not in entry.aliases:
                    entry.aliases = [*entry.aliases, target_id]

    def resolve_runtime(self, model_id: str) -> AvailableModel | str:
        key = self.resolve_id(model_id)
        if key in self._runtime:
            return self._runtime[key]
        # Stable image aliases (gemini-2.5-flash-image, etc.) live in
        # our registry but not in gemini-webapi's runtime.  Fall back
        # to the first alias in the entry's alias list — that's the
        # underlying real model id (e.g. gemini-3-flash) the alias
        # routes to.
        entry = self._entries.get(key)
        if entry and entry.aliases:
            for alias in entry.aliases:
                if alias in self._runtime:
                    return self._runtime[alias]
        return key

    def resolve_id(self, model_id: str) -> str:
        if not model_id:
            return model_id
        if model_id in self._entries:
            return model_id
        slug = _slug(model_id)
        if slug in self._alias_index:
            return self._alias_index[slug]
        for entry in self._entries.values():
            if model_id in entry.aliases or slug in {_slug(a) for a in entry.aliases}:
                return entry.id
            if model_id.lower() in entry.id.lower() or entry.id.lower() in model_id.lower():
                return entry.id
        return model_id

    def pick_image_model(self, requested: str | None = None) -> str:
        if requested:
            resolved = self.resolve_id(requested)
            entry = self._entries.get(resolved)
            if entry and (entry.image_ok or entry.kind in {"image", "both"}):
                return resolved
        for entry in self._entries.values():
            if entry.image_ok:
                return entry.id
        for entry in self._entries.values():
            if entry.kind in {"image", "both"} or "image" in entry.id.lower():
                return entry.id
        for entry in self._entries.values():
            if entry.chat_ok and "flash" in entry.id.lower():
                return entry.id
        if self._entries:
            return next(iter(self._entries.keys()))
        return "gemini-3-flash"

    def pick_chat_model(self, requested: str | None = None) -> str:
        if requested:
            resolved = self.resolve_id(requested)
            entry = self._entries.get(resolved)
            if entry and entry.kind != "image":
                return resolved
        for entry in self._entries.values():
            if entry.chat_ok and entry.kind != "image":
                return entry.id
        for entry in self._entries.values():
            if "image" not in entry.id.lower():
                return entry.id
        return "gemini-3-flash"

    def update_probe(
        self, model_id: str, *, chat_ok: bool | None = None, image_ok: bool | None = None
    ) -> None:
        entry = self._entries.get(model_id)
        if not entry:
            return
        if chat_ok is not None:
            entry.chat_ok = chat_ok
        if image_ok is not None:
            entry.image_ok = image_ok
        if entry.chat_ok and entry.image_ok:
            entry.kind = "both"
        elif entry.image_ok:
            entry.kind = "image"
        elif entry.chat_ok:
            entry.kind = "chat"
        entry.probed_at = int(time.time())

    def list_openai_models(
        self, *, image_overrides: set[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return the small curated set of entries the client can pick.

        We deliberately publish a *fixed* set of model ids so the
        client can rely on a stable choice.  The proxy knows about
        at most:

        * One chat entry per available chat backend (gemini-3-flash
          plus, when present, gemini-3-pro).
        * The two stable image aliases (``gemini-2.5-flash-image``,
          ``gemini-2.5-pro-image``) regardless of whether the
          underlying gemini-webapi call currently succeeds — the
          403/error is surfaced at request time.

        Auto-generated aliases (``gemini-2.0-flash``,
        ``gemini-3-flash-preview``, ``gemini-advanced``, ...) and
        the empty-id entry that gemini-webapi sometimes returns are
        kept in the registry for inbound ``resolve_id`` so older
        clients can still send them, but are NOT exposed in the
        model list.
        """
        created = int(time.time())
        out: list[dict[str, Any]] = []

        # 1. Image aliases — always present, always marked image-capable.
        for alias_id in self._IMAGE_ALIAS_IDS:
            entry = self._entries.get(alias_id)
            if entry is not None:
                out.append(entry.to_openai(created, image_overrides=image_overrides))

        # 2. Chat entries — one per distinct chat backend that has
        #    either been probed as chat_ok or is named chat by the
        #    kind heuristic.  Skip entries with no chat backend.
        seen_chat: set[str] = set()
        for entry in self._entries.values():
            if entry.id in self._IMAGE_ALIAS_IDS:
                continue
            if not (entry.chat_ok or entry.kind in {"chat", "both"}):
                continue
            if entry.id in seen_chat:
                continue
            seen_chat.add(entry.id)
            out.append(entry.to_openai(created, image_overrides=image_overrides))

        return sorted(out, key=lambda x: x["id"])
