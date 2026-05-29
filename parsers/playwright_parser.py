"""Загрузка HTML через Playwright + системный Chrome, сохранение cookie.json."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright

from parsers import headers as hdr
from parsers.utils import COOKIE_FILE, pick_user_agent, random_delay

logger = logging.getLogger(__name__)

CHROME_PATH = os.environ.get(
    "CHROME_PATH",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)
LENTA_URL = "https://lenta.ru/"


async def fetch_lenta_html(
    cookie_path: Path | None = None,
    chrome_executable: str | None = None,
) -> str:
    """Открывает главную Lenta.ru, сохраняет storage_state в cookie.json."""
    random_delay()
    exe = chrome_executable or CHROME_PATH
    if not Path(exe).is_file():
        raise FileNotFoundError(f"Chrome не найден по пути: {exe}")

    out_path = cookie_path or COOKIE_FILE
    ua = pick_user_agent()
    extra_headers = {**hdr.CUSTOM_HEADERS, "User-Agent": ua}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path=exe,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            context = await browser.new_context(
                user_agent=ua,
                extra_http_headers=extra_headers,
                locale="ru-RU",
            )
            page = await context.new_page()
            await page.goto(LENTA_URL, wait_until="domcontentloaded", timeout=120_000)
            await page.wait_for_timeout(8_000)
            html = await page.content()
            await context.storage_state(path=str(out_path))
            await context.close()
        finally:
            await browser.close()

    logger.info("Playwright: HTML сохранён, куки записаны в %s", out_path)
    if not html:
        raise ValueError("Пустой HTML от Playwright")
    return html
