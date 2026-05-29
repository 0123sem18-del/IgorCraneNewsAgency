"""
Пример вызова ChatGPT через ProxyAPI (синхронный скрипт для терминала).
Использует ту же логику, что и веб-приложение: ключ из OPENAI_API_KEY.

Запуск из корня проекта (с активированным venv):
    python ResponsesAPI.py
"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

# Загружаем .env из каталога проекта (если есть)
load_dotenv()

from assistant_openai import ask_chatgpt


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "Задайте переменную окружения OPENAI_API_KEY "
            "(или добавьте её в файл .env в корне проекта).",
            file=sys.stderr,
        )
        sys.exit(1)

    reply = await ask_chatgpt("Привет!")
    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
