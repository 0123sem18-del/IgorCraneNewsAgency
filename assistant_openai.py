"""Асинхронный клиент ChatGPT через ProxyAPI (OpenAI-совместимый API)."""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

logger = logging.getLogger(__name__)

# ProxyAPI для OpenAI-совместимого API ожидает префикс /openai/v1:
# документация: https://proxyapi.ru/docs/openai-text-generation
_DEFAULT_BASE_URL = "https://api.proxyapi.ru/openai/v1"

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Ленивая инициализация клиента OpenAI SDK."""
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY не задан в окружении или .env")
        base_url = os.environ.get("OPENAI_BASE_URL", _DEFAULT_BASE_URL)
        _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    return _client


async def ask_chatgpt(prompt: str) -> str:
    """
    Отправляет промпт в модель и возвращает текст ответа.
    Модель по умолчанию: gpt-4o-mini (переопределяется через OPENAI_MODEL).
    """
    client = _get_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    logger.info("Запрос к ProxyAPI, модель: %s", model)
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.7,
    )
    text = response.choices[0].message.content
    result = (text or "").strip()
    logger.info("Ответ ProxyAPI получен (%s символов)", len(result))
    return result
