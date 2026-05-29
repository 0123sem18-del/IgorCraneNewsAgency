"""Единая настройка логирования в консоль (сообщения на русском)."""

from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv

# Имена уровней в логах — по-русски
_LEVEL_NAMES = {
    logging.DEBUG: "ОТЛАДКА",
    logging.INFO: "ИНФО",
    logging.WARNING: "ПРЕДУПРЕЖДЕНИЕ",
    logging.ERROR: "ОШИБКА",
    logging.CRITICAL: "КРИТИЧНО",
}


class RussianLevelFormatter(logging.Formatter):
    """Формат времени, уровня и модуля; уровень — русской подписью."""

    def format(self, record: logging.LogRecord) -> str:
        record.levelname = _LEVEL_NAMES.get(record.levelno, record.levelname)
        return super().format(record)


def setup_console_logging(level: str | None = None) -> None:
    """
    Настраивает вывод логов в stdout.
    Уровень берётся из аргумента или переменной LOG_LEVEL в .env (по умолчанию INFO).
    """
    load_dotenv()

    raw = (level or os.environ.get("LOG_LEVEL", "INFO")).strip().upper()
    numeric = getattr(logging, raw, logging.INFO)

    formatter = RussianLevelFormatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric)

    # Меньше англоязычного шума от HTTP-клиентов; события приложения — на русском
    for noisy in ("httpx", "httpcore", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger(__name__).info(
        "Логирование в консоль включено, уровень: %s", raw
    )
