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

    def to_openai(self, created: int) -> dict[str, Any]:
        return {
            "id": self.id,
            "object": "model",
            "created": created,
            "owned_by": "google",
            "capabilities": {
                "chat": self.chat_ok or self.kind in {"chat", "both"},
                "image": self.image_ok or self.kind in {"image", "both"},
            },
        }


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", name.lower()).strip("-")


def _guess_kind(model_name: str, description: str) -> str:
    blob = f"{model_name} {description}".lower()
    if any(x in blob for x in TEXT_BLOCKLIST):
        return "chat"
    has_image = any(x in blob for x in IMAGE_HINTS)
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
            return
        raw = json.loads(path.read_text())
        for item in raw.get("models", []):
            entry = ModelEntry(**item)
            self._entries[entry.id] = entry
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
        self._rebuild_aliases()
        self._loaded = True

    def _rebuild_aliases(self) -> None:
        self._alias_index.clear()
        for entry in self._entries.values():
            self._alias_index[_slug(entry.id)] = entry.id
            for alias in entry.aliases:
                self._alias_index[_slug(alias)] = entry.id

    def resolve_runtime(self, model_id: str) -> AvailableModel | str:
        key = self.resolve_id(model_id)
        if key in self._runtime:
            return self._runtime[key]
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

    def list_openai_models(self) -> list[dict[str, Any]]:
        created = int(time.time())
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for entry in self._entries.values():
            if entry.id in seen:
                continue
            seen.add(entry.id)
            out.append(entry.to_openai(created))
            for alias in entry.aliases:
                if alias in seen:
                    continue
                seen.add(alias)
                clone = ModelEntry(
                    id=alias,
                    display_name=entry.display_name,
                    description=entry.description,
                    kind=entry.kind,
                    chat_ok=entry.chat_ok,
                    image_ok=entry.image_ok,
                    probed_at=entry.probed_at,
                    aliases=[],
                )
                out.append(clone.to_openai(created))
        return sorted(out, key=lambda x: x["id"])
