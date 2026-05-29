"""Чтение/проверка Playwright storage_state (cookie.json)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parsers.utils import COOKIE_FILE


def cookies_file_valid(path: Path | None = None) -> bool:
    p = path or COOKIE_FILE
    if not p.is_file() or p.stat().st_size < 12:
        return False
    try:
        data: Any = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    cookies = data.get("cookies")
    if not isinstance(cookies, list) or not cookies:
        return False
    return any("lenta" in str(c.get("domain", "")).lower() for c in cookies)


def cookies_dict_for_lenta(path: Path | None = None) -> dict[str, str]:
    p = path or COOKIE_FILE
    if not p.is_file():
        return {}
    try:
        data: Any = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    out: dict[str, str] = {}
    for c in data.get("cookies") or []:
        dom = str(c.get("domain") or "").lower().lstrip(".")
        if dom.endswith("lenta.ru"):
            name = c.get("name")
            val = c.get("value")
            if name and val is not None:
                out[str(name)] = str(val)
    return out
