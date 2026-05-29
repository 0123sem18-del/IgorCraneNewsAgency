"""PostgreSQL (asyncpg): схема, пул соединений, чтение и запись новостей."""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

import asyncpg
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Таймаут одного запроса к БД — чтобы страница не «висела» минутами
DB_QUERY_TIMEOUT_SEC = 5

DbHandle = asyncpg.Pool | asyncpg.Connection
_CONNECTION_ERRORS: tuple[type[BaseException], ...] = (
    asyncpg.exceptions.ConnectionDoesNotExistError,
    asyncpg.exceptions.ConnectionFailureError,
    asyncpg.exceptions.InterfaceError,
    ConnectionResetError,
    OSError,
)

_MONTHS_GEN = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)

INIT_NEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL UNIQUE,
    link TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    published_at TIMESTAMPTZ,
    source TEXT NOT NULL DEFAULT '',
    ai_context TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_published_at ON news (published_at DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_news_category ON news (category);
"""


def _format_exc(exc: BaseException) -> str:
    text = str(exc).strip()
    return text if text else repr(exc)


async def _with_db_retry(pool: asyncpg.Pool, operation: str, coro_factory):
    """
    Повтор запроса при обрыве соединения (WinError 10054 и аналоги).
    Перед второй попыткой сбрасывает простаивающие соединения в пуле.
    """
    last_exc: BaseException | None = None
    for attempt in range(1, 3):
        try:
            return await coro_factory()
        except _CONNECTION_ERRORS as exc:
            last_exc = exc
            logger.warning(
                "%s: сбой соединения (попытка %s/2): %s",
                operation,
                attempt,
                _format_exc(exc),
            )
            if attempt < 2:
                await pool.expire_connections()
                continue
    assert last_exc is not None
    raise last_exc


async def _expire_stale(db: DbHandle) -> None:
    """Сброс «битых» соединений только для пула (не для отдельного conn RSS)."""
    if isinstance(db, asyncpg.Pool):
        await db.expire_connections()


async def connect_direct() -> asyncpg.Connection:
    """Отдельное соединение с минимальным набором параметров."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL не задан")
    return await asyncpg.connect(
        dsn,
        ssl=True,
        command_timeout=30,
    )


async def create_pool() -> asyncpg.Pool | None:
    """
    Создаёт пул подключений к PostgreSQL.
    При ошибке возвращает None — приложение работает на fallback.
    """
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL не задан в .env (см. .env.example)")
        return None

    try:
        pool = await asyncpg.create_pool(
            dsn,
            ssl=True,
            min_size=1,
            max_size=5,
            command_timeout=30,
            max_inactive_connection_lifetime=300,
        )
        logger.info("Пул соединений PostgreSQL создан")
        return pool
    except Exception as exc:
        logger.error("ТИП ОШИБКИ: %s", type(exc).__name__)
        logger.error("ДЕТАЛИ ОШИБКИ: %s", _format_exc(exc))
        return None


async def init_db_direct() -> None:
    """Миграция схемы через отдельное соединение (без пула)."""
    conn = await connect_direct()
    try:
        await conn.execute(INIT_NEWS_TABLE_SQL)
    finally:
        await conn.close()
    logger.info("Схема БД news проверена/создана")


async def init_db(pool: asyncpg.Pool) -> None:
    """Миграция: таблица news и индексы (legacy, через пул)."""
    async with pool.acquire() as conn:
        await conn.execute(INIT_NEWS_TABLE_SQL)
    logger.info("Схема БД news проверена/создана")


async def save_news_if_new(
    db: DbHandle,
    *,
    title: str,
    link: str,
    category: str,
    published_at: datetime | None,
    source: str,
) -> bool:
    """
    Сохраняет новость. При дубликате заголовка (UNIQUE) — пропуск.
    db — пул (HTTP) или отдельное соединение (RSS).
    """
    title = (title or "").strip()
    link = (link or "").strip()
    if not title or not link:
        return False

    if published_at and published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    try:
        status = await asyncio.wait_for(
            db.execute(
                """
                INSERT INTO news (title, link, category, published_at, source)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (title) DO NOTHING
                """,
                title,
                link,
                (category or source or "Новости").strip(),
                published_at,
                (source or "").strip(),
            ),
            timeout=DB_QUERY_TIMEOUT_SEC,
        )
        if status.endswith("1"):
            logger.debug("В БД добавлена новость: «%s»", title[:60])
            return True
        return False
    except asyncio.TimeoutError:
        logger.warning("Таймаут сохранения новости «%s» — пропуск", title[:60])
        await _expire_stale(db)
        return False
    except _CONNECTION_ERRORS as exc:
        logger.warning(
            "Не удалось сохранить новость «%s»: %s",
            title[:60],
            _format_exc(exc),
        )
        await _expire_stale(db)
        return False
    except Exception as exc:
        logger.warning("Не удалось сохранить новость «%s»: %s", title[:60], exc)
        return False


def _format_published(dt: datetime | None) -> tuple[str, str, str]:
    if not dt:
        return "", "", ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    date_display = f"{dt.day} {_MONTHS_GEN[dt.month - 1]} {dt.year}"
    time_display = dt.strftime("%H:%M")
    return date_display, time_display, dt.isoformat()


def record_to_template_item(row: asyncpg.Record) -> dict[str, Any]:
    """Преобразует строку БД в формат, ожидаемый шаблоном index.html."""
    pub = row["published_at"]
    date_display, time_display, datetime_iso = _format_published(pub)
    return {
        "id": row["id"],
        "title": row["title"],
        "url": row["link"],
        "category": row["category"] or row["source"] or "Новости",
        "time_display": time_display,
        "date_display": date_display,
        "datetime_iso": datetime_iso,
        "image_url": "",
        "lead": "",
        "source": row["source"],
    }


async def fetch_news_direct(
    *,
    topic: str | None = None,
    limit: int = 50,
) -> list[asyncpg.Record]:
    """Чтение новостей через отдельное соединение (жёсткий таймаут 8 с на всё)."""
    topic = (topic or "").strip()

    async def _query() -> list[asyncpg.Record]:
        conn = await connect_direct()
        try:
            if topic:
                pattern = f"%{topic}%"
                return await conn.fetch(
                    """
                    SELECT id, title, link, category, published_at, source, ai_context
                    FROM news
                    WHERE title ILIKE $1 OR category ILIKE $1
                    ORDER BY published_at DESC NULLS LAST
                    LIMIT $2
                    """,
                    pattern,
                    limit,
                )
            return await conn.fetch(
                """
                SELECT id, title, link, category, published_at, source, ai_context
                FROM news
                ORDER BY published_at DESC NULLS LAST
                LIMIT $1
                """,
                limit,
            )
        finally:
            await conn.close()

    return await asyncio.wait_for(_query(), timeout=8.0)


async def get_news_by_title_direct(title: str) -> asyncpg.Record | None:
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncio.wait_for(connect_direct(), timeout=DB_QUERY_TIMEOUT_SEC)
        return await asyncio.wait_for(
            conn.fetchrow(
                """
                SELECT id, title, ai_context
                FROM news
                WHERE title = $1
                """,
                title.strip(),
            ),
            timeout=DB_QUERY_TIMEOUT_SEC,
        )
    finally:
        if conn is not None:
            await conn.close()


async def update_ai_context_direct(news_id: int, context: str) -> None:
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncio.wait_for(connect_direct(), timeout=DB_QUERY_TIMEOUT_SEC)
        await asyncio.wait_for(
            conn.execute(
                "UPDATE news SET ai_context = $1 WHERE id = $2",
                context,
                news_id,
            ),
            timeout=DB_QUERY_TIMEOUT_SEC,
        )
    finally:
        if conn is not None:
            await conn.close()


async def fetch_news(
    pool: asyncpg.Pool,
    *,
    topic: str | None = None,
    limit: int = 50,
) -> list[asyncpg.Record]:
    """Последние новости; при topic — фильтр ILIKE по title и category."""
    topic = (topic or "").strip()

    async def _run() -> list[asyncpg.Record]:
        if topic:
            pattern = f"%{topic}%"
            return await pool.fetch(
                """
                SELECT id, title, link, category, published_at, source, ai_context
                FROM news
                WHERE title ILIKE $1 OR category ILIKE $1
                ORDER BY published_at DESC NULLS LAST
                LIMIT $2
                """,
                pattern,
                limit,
            )
        return await pool.fetch(
            """
            SELECT id, title, link, category, published_at, source, ai_context
            FROM news
            ORDER BY published_at DESC NULLS LAST
            LIMIT $1
            """,
            limit,
        )

    try:
        return await asyncio.wait_for(_run(), timeout=DB_QUERY_TIMEOUT_SEC)
    except _CONNECTION_ERRORS:
        await pool.expire_connections()
        return await asyncio.wait_for(_run(), timeout=DB_QUERY_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        await pool.expire_connections()
        raise


async def get_news_by_title(pool: asyncpg.Pool, title: str) -> asyncpg.Record | None:
    async def _run() -> asyncpg.Record | None:
        return await pool.fetchrow(
            """
            SELECT id, title, ai_context
            FROM news
            WHERE title = $1
            """,
            title.strip(),
        )

    return await asyncio.wait_for(
        _with_db_retry(pool, "get_news_by_title", _run),
        timeout=DB_QUERY_TIMEOUT_SEC,
    )


async def update_ai_context(pool: asyncpg.Pool, news_id: int, context: str) -> None:
    async def _run() -> None:
        await pool.execute(
            "UPDATE news SET ai_context = $1 WHERE id = $2",
            context,
            news_id,
        )

    await asyncio.wait_for(
        _with_db_retry(pool, "update_ai_context", _run),
        timeout=DB_QUERY_TIMEOUT_SEC,
    )


def rows_to_page_data(rows: list[asyncpg.Record]) -> dict[str, Any]:
    """Раскладывает до 50 записей по блокам вёрстки."""
    if not rows:
        return {}

    items = [record_to_template_item(r) for r in rows]
    hero = dict(items[0])
    daily = [dict(x) for x in items[:6]]
    grid = [dict(x) for x in items[1:5]]
    while len(grid) < 4 and len(items) > len(grid) + 1:
        idx = len(grid) + 1
        if idx < len(items):
            grid.append(dict(items[idx]))
        else:
            break

    popular_featured = dict(items[5]) if len(items) > 5 else dict(items[0])
    popular_list = [dict(x) for x in items[6:9]]
    if len(popular_list) < 3:
        for x in items[1:]:
            if len(popular_list) >= 3:
                break
            if x["title"] not in {p["title"] for p in popular_list} and x["title"] != popular_featured.get("title"):
                popular_list.append(dict(x))

    return {
        "daily_news": daily,
        "main_hero": hero,
        "main_grid": grid[:4],
        "popular_featured": popular_featured,
        "popular_list": popular_list[:3],
    }
