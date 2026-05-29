"""Гибрид: при необходимости Playwright (куки), затем curl_cffi."""

from __future__ import annotations

import asyncio
import logging

from parsers.cookie_store import cookies_dict_for_lenta, cookies_file_valid
from parsers.curl_parser import fetch_lenta_html as curl_fetch
from parsers.lenta_parse import is_bot_challenge_page
from parsers.playwright_parser import fetch_lenta_html as playwright_fetch
from parsers.utils import COOKIE_FILE, random_delay

logger = logging.getLogger(__name__)


async def fetch_lenta_html() -> str:
    if not cookies_file_valid(COOKIE_FILE):
        logger.info("hybrid: cookie.json отсутствует или невалиден — Playwright")
        await playwright_fetch()

    cookies = cookies_dict_for_lenta(COOKIE_FILE)

    def _curl() -> str:
        random_delay()
        return curl_fetch(cookies=cookies or None)

    html = await asyncio.to_thread(_curl)

    if is_bot_challenge_page(html) or len(html) < 8000:
        logger.info("hybrid: похоже на challenge — обновляем куки через Playwright")
        await playwright_fetch()
        cookies = cookies_dict_for_lenta(COOKIE_FILE)
        html = await asyncio.to_thread(lambda: curl_fetch(cookies=cookies or None))

    return html
