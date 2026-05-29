import ssl
import os

async def create_pool() -> asyncpg.Pool | None:
    dsn = os.getenv("DATABASE_URL")
    
    # Путь к сертификату в корне проекта
    cert_path = os.path.join(os.path.dirname(__file__), "aiven.crt")
    
    # Если сертификата нет, код все равно попытается подключиться (но может упасть)
    if not os.path.exists(cert_path):
        logger.warning("Файл сертификата aiven.crt не найден! SSL соединение может не работать.")

    # Настройка SSL
    ctx = ssl.create_default_context(cafile=cert_path if os.path.exists(cert_path) else None)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED

    try:
        return await asyncpg.create_pool(
            _normalize_dsn(dsn),
            ssl=ctx,
            min_size=1,
            max_size=10
        )
    except Exception as e:
        logger.error(f"Критическая ошибка подключения к БД: {e}")
        return None
