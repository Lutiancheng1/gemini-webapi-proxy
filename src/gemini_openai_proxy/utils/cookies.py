from __future__ import annotations


def parse_cookie_string(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw_part in raw.split(";"):
        part = raw_part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        value = value.strip()
        if name:
            out[name] = value
    return out
