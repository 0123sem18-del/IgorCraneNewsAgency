import ssl  # 1. Добавьте этот импорт в начало файла

# ... (остальной код)

async def create_pool() -> asyncpg.Pool | None:
    """Создает пул соединений с PostgreSQL."""
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        logger.error("DATABASE_URL не найден в переменных окружения")
        return None

    # 2. Создаем SSL-контекст для обхода ошибки проверки сертификата на Windows
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        return await asyncpg.create_pool(
            _normalize_dsn(dsn),
            ssl=ctx,  # 3. Передаем контекст сюда
            min_size=1,
            max_size=10
        )
    except Exception as e:
        logger.error("Не удалось подключиться к PostgreSQL (проверьте сеть, VPN и DATABASE_URL): %s", e)
        return None