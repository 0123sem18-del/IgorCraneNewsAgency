"""FastAPI: новостной агрегатор (RSS → PostgreSQL → веб)."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from logging_config import setup_console_logging

setup_console_logging()

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from assistant_openai import ask_chatgpt
from database import (
    fetch_news_direct,
    get_news_by_title_direct,
    init_db_direct,
    rows_to_page_data,
    update_ai_context_direct,
)
from parsers.fallback_data import get_fallback
from rss_collector import rss_background_loop

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent

_ai_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Схема БД и RSS — в фоне; HTTP отвечает сразу."""
    app.state.rss_task = None

    async def _startup_db() -> None:
        logger.info("Фоновая инициализация PostgreSQL и RSS")
        try:
            await init_db_direct()
            logger.info("PostgreSQL: схема готова")
            app.state.rss_task = asyncio.create_task(rss_background_loop())
            logger.info("Фоновый сбор RSS запущен (повтор каждые 15 минут)")
        except Exception:
            logger.exception("Ошибка инициализации БД; RSS-сборщик не запущен")

    asyncio.create_task(_startup_db())
    logger.info("Приложение запущено — HTTP готов, БД подключается в фоне")

    yield

    logger.info("Остановка приложения")
    rss_task = app.state.rss_task
    if rss_task is not None:
        rss_task.cancel()
        try:
            await rss_task
        except asyncio.CancelledError:
            logger.info("Фоновый сбор RSS остановлен")


app = FastAPI(
    title="Новостное агентство (RSS + PostgreSQL)",
    lifespan=lifespan,
)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/styles", StaticFiles(directory=str(BASE_DIR / "styles")), name="styles")
app.mount("/Img", StaticFiles(directory=str(BASE_DIR / "Img")), name="img")
app.mount("/js", StaticFiles(directory=str(BASE_DIR / "js")), name="js")


@app.get("/health")
async def health():
    """Быстрая проверка: сервер жив, БД не трогаем."""
    return {"status": "ok"}


@app.get("/")
async def index(
    request: Request,
    topic: str | None = Query(None, description="Фильтр по теме/категории"),
):
    logger.info("GET / — запрос получен")
    raw_topic = (topic or "").strip()
    if not raw_topic or raw_topic.lower() == "главная":
        current_topic = "Главная"
    else:
        current_topic = raw_topic

    try:
        rows = await fetch_news_direct(topic=None if current_topic == "Главная" else current_topic)
        data = rows_to_page_data(rows) or get_fallback()
    except Exception as exc:
        logger.warning("GET / — не удалось загрузить новости из БД, fallback: %s", exc)
        data = get_fallback()

    logger.info("GET / — ответ, тема: «%s»", current_topic)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "current_topic": current_topic, **data},
    )


@app.get("/api/context")
async def api_context(
    title: str = Query(..., min_length=1, description="Заголовок новости"),
):
    """ИИ-эксперт: кэш в news.ai_context, иначе ProxyAPI и UPDATE в БД."""
    title = title.strip()
    err_msg = "Не удалось загрузить комментарий эксперта. Попробуйте позже."

    if not title:
        return JSONResponse({"context": err_msg}, status_code=400)

    row = None
    try:
        row = await get_news_by_title_direct(title)
    except Exception as exc:
        logger.warning("Ошибка чтения ai_context из БД: %s", exc)

    if row and row["ai_context"]:
        logger.info("ИИ-контекст: ответ из кэша БД для «%s»", title[:80])
        return {"context": row["ai_context"]}

    logger.info("ИИ-контекст: запрос к модели для «%s»", title[:80])
    prompt = (
        f"Новость: '{title}'. Объясни простыми словами, почему это событие "
        "важно для обычного человека в России, в 1-2 предложениях."
    )

    try:
        answer = await ask_chatgpt(prompt)
        if not answer:
            raise ValueError("Пустой ответ от модели")

        if row:
            async with _ai_lock:
                try:
                    await update_ai_context_direct(row["id"], answer)
                    logger.info("ИИ-контекст: ответ сохранён в БД (id=%s)", row["id"])
                except Exception as exc:
                    logger.warning("Не удалось сохранить ai_context в БД: %s", exc)

        logger.info("ИИ-контекст: ответ модели получен успешно")
        return {"context": answer}
    except Exception as exc:
        logger.exception("Ошибка ProxyAPI / ChatGPT: %s", exc)
        return {"context": err_msg}
