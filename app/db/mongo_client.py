from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

# Глобальный клиент - инициализируется в lifespan приложения
_mongo_client: AsyncIOMotorClient | None = None


def get_mongo_db() -> AsyncIOMotorDatabase:
    """Возвращает объект базы данных MongoDB"""
    if _mongo_client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return _mongo_client[settings.mongo_db]


async def init_mongo() -> None:
    """Создаёт клиент MongoDB. Вызывается в lifespan приложения"""
    global _mongo_client
    _mongo_client = AsyncIOMotorClient(settings.mongo_url)


async def close_mongo() -> None:
    """Закрывает соединение с MongoDB. Вызывается при завершении приложения"""
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None
