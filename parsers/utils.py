"""Утилиты: User-Agent, задержки, пути проекта."""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path

from parsers.headers import CUSTOM_HEADERS

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
USER_AGENT_FILE = PROJECT_ROOT / "user_agent_pc.txt"
COOKIE_FILE = PROJECT_ROOT / "cookie.json"
CHROME_DEFAULT = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

_DEFAULT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def load_user_agents() -> list[str]:
    if not USER_AGENT_FILE.is_file():
        return list(_DEFAULT_UAS)
    lines = [
        ln.strip()
        for ln in USER_AGENT_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    return lines or list(_DEFAULT_UAS)


def pick_user_agent() -> str:
    return random.choice(load_user_agents())


def random_delay(min_s: float = 0.35, max_s: float = 1.25) -> None:
    time.sleep(random.uniform(min_s, max_s))


def build_headers() -> dict[str, str]:
    h = dict(CUSTOM_HEADERS)
    h["User-Agent"] = pick_user_agent()
    return h
