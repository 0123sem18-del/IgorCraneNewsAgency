"""Проверка подключения к PostgreSQL (Aiven) из .env."""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from database import _aiven_ssl_context, _format_exc, _normalize_dsn


async def test() -> None:
    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        print("Ошибка: DATABASE_URL не задан в .env")
        sys.exit(1)

    print("Попытка подключения (SSL + aiven.crt, таймаут 30 с)...")
    try:
        import asyncpg

        conn = await asyncpg.connect(
            _normalize_dsn(dsn),
            ssl=_aiven_ssl_context(),
            timeout=30,
        )
        version = await conn.fetchval("SELECT version()")
        print("УСПЕХ! Подключение установлено.")
        print(f"Сервер: {version[:80]}...")
        await conn.close()
    except Exception as exc:
        print(f"ТИП ОШИБКИ: {type(exc).__name__}")
        print(f"ДЕТАЛИ ОШИБКИ: {_format_exc(exc)}")
        if type(exc).__name__ == "TimeoutError":
            print(
                "Подсказка: таймаут — проверьте VPN, фаервол, порт 17110 "
                "и список Allowed IP в Aiven Console."
            )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test())
