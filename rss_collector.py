"""Фоновый сбор RSS-лент и запись в PostgreSQL."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import mktime
from typing import Any

import feedparser

from database import connect_direct, save_news_if_new

logger = logging.getLogger(__name__)

# Источники в JSON-формате (как в ТЗ; URL Коммерсанта исправлен на рабочий)
RSS_SOURCES: list[dict[str, str]] = json.loads(
    """
[
  {
    "source": "РБК",
    "url": "https://rssexport.rbc.ru/rbc/top/rssexport.rbc.ru/news.rss",
    "category": "Экономика"
  },
  {
    "source": "Коммерсантъ",
    "url": "https://www.kommersant.ru/RSS/news.xml",
    "category": "Экономика"
  },
  {
    "source": "Ведомости",
    "url": "https://www.vedomosti.ru/rss/news.xml",
    "category": "Экономика"
  },
  {
    "source": "N+1",
    "url": "https://nplus1.ru/rss",
    "category": "Наука"
  }
]
"""
)

ITEMS_PER_FEED = 10
RSS_POLL_INTERVAL_SEC = 900  # 15 минут


def _entry_published(entry: Any) -> datetime | None:
    """Дата публикации из RSS (published / updated)."""
    if getattr(entry, "published_parsed", None):
        try:
            return datetime.fromtimestamp(
                mktime(entry.published_parsed), tz=timezone.utc
            )
        except (OverflowError, ValueError, TypeError):
            pass
    if getattr(entry, "updated_parsed", None):
        try:
            return datetime.fromtimestamp(
                mktime(entry.updated_parsed), tz=timezone.utc
            )
        except (OverflowError, ValueError, TypeError):
            pass
    pub = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if pub:
        try:
            dt = parsedate_to_datetime(pub)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (TypeError, ValueError):
            pass
    return None


def _entry_category(entry: Any, default: str) -> str:
    tags = getattr(entry, "tags", None) or []
    for tag in tags:
        term = (getattr(tag, "term", None) or "").strip()
        if term:
            return term
    return default


def _parse_feed(source_cfg: dict[str, str]) -> list[dict[str, Any]]:
    """Синхронный разбор одной ленты (вызывается в thread pool)."""
    url = source_cfg["url"]
    source_name = source_cfg["source"]
    default_category = source_cfg.get("category", source_name)

    parsed = feedparser.parse(
        url,
        agent="NewsAggregator/1.0 (+https://lenta.ru/)",
    )
    if getattr(parsed, "bozo", False) and not parsed.entries:
        exc = getattr(parsed, "bozo_exception", None)
        logger.warning("RSS %s: ошибка разбора — %s", source_name, exc)
        return []

    items: list[dict[str, Any]] = []
    for entry in parsed.entries[:ITEMS_PER_FEED]:
        title = (getattr(entry, "title", None) or "").strip()
        link = (getattr(entry, "link", None) or "").strip()
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "category": _entry_category(entry, default_category),
                "published_at": _entry_published(entry),
                "source": source_name,
            }
        )
    return items


async def update_news_db() -> int:
    """
    Обходит RSS-источники и пишет в PostgreSQL через отдельное соединение,
    чтобы не блокировать пул для HTTP-запросов сайта.
    """
    inserted = 0
    conn = None
    try:
        conn = await connect_direct()
    except Exception as exc:
        logger.error("RSS: не удалось подключиться к БД: %s", exc)
        return 0

    try:
        for source_cfg in RSS_SOURCES:
            source_name = source_cfg.get("source", "?")
            try:
                entries = await asyncio.to_thread(_parse_feed, source_cfg)
            except Exception as exc:
                logger.exception("RSS %s: не удалось загрузить — %s", source_name, exc)
                continue

            for entry in entries:
                try:
                    if await save_news_if_new(conn, **entry):
                        inserted += 1
                except Exception as exc:
                    logger.warning(
                        "RSS %s: пропуск «%s» — %s",
                        source_name,
                        entry.get("title", "")[:50],
                        exc,
                    )

            logger.info("RSS %s: обработано %s записей", source_name, len(entries))
    finally:
        if conn is not None:
            await conn.close()

    logger.info("RSS-сбор завершён: добавлено %s новых новостей", inserted)
    return inserted


async def rss_background_loop() -> None:
    """Периодический сбор RSS каждые 15 минут."""
    logger.info("Цикл фонового RSS-сбора начат")
    await asyncio.sleep(10)
    while True:
        try:
            await update_news_db()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Ошибка фонового RSS-сбора")
        logger.info(
            "Следующий сбор RSS через %s мин", RSS_POLL_INTERVAL_SEC // 60
        )
        await asyncio.sleep(RSS_POLL_INTERVAL_SEC)
