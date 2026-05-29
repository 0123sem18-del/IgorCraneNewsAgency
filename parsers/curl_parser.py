"""Загрузка HTML через curl_cffi (impersonate=chrome110)."""

from __future__ import annotations

import logging

from curl_cffi import requests

from parsers.utils import build_headers, random_delay

logger = logging.getLogger(__name__)

LENTA_URL = "https://lenta.ru/"


def fetch_lenta_html(cookies: dict[str, str] | None = None) -> str:
    random_delay()
    headers = build_headers()
    session = requests.Session(impersonate="chrome110")
    session.headers.update(headers)
    if cookies:
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=".lenta.ru", path="/")
    resp = session.get(LENTA_URL, timeout=45, allow_redirects=True)
    resp.raise_for_status()
    if not resp.text:
        raise ValueError("Пустой ответ")
    logger.debug("curl_cffi: получено %s байт", len(resp.text))
    return resp.text


def fetch_url_html(url: str, cookies: dict[str, str] | None = None) -> str:
    """Загрузка произвольного URL через curl_cffi (с теми же заголовками/куками)."""
    random_delay()
    headers = build_headers()
    session = requests.Session(impersonate="chrome110")
    session.headers.update(headers)
    if cookies:
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=".lenta.ru", path="/")
    resp = session.get(url, timeout=45, allow_redirects=True)
    resp.raise_for_status()
    if not resp.text:
        raise ValueError("Пустой ответ")
    logger.debug("curl_cffi: получено %s байт (%s)", len(resp.text), url)
    return resp.text
