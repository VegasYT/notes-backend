import uuid

import redis.asyncio as aioredis

from app.core.config import settings

# Глобальный пул соединений - инициализируется при старте приложения
redis_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """Возвращает активный клиент Redis из пула соединений"""
    if redis_pool is None:
        raise RuntimeError("Redis pool is not initialized")
    return redis_pool


async def init_redis() -> None:
    """Создаёт пул соединений с Redis. Вызывается в lifespan приложения"""
    global redis_pool
    redis_pool = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def close_redis() -> None:
    """Закрывает пул соединений с Redis. Вызывается при завершении приложения"""
    global redis_pool
    if redis_pool:
        await redis_pool.aclose()
        redis_pool = None


class SessionStore:
    """Управляет сессиями пользователей в Redis"""

    _PREFIX = "session:"

    def __init__(self, client: aioredis.Redis) -> None:
        self._client = client

    async def create(self, user_id: int) -> str:
        """Создаёт новую сессию и возвращает session_id (UUID)"""
        session_id = str(uuid.uuid4())
        key = self._PREFIX + session_id
        await self._client.set(key, str(user_id), ex=settings.redis_session_ttl)
        return session_id

    async def get_user_id(self, session_id: str) -> int | None:
        """Возвращает user_id по session_id или None, если сессия не найдена/истекла"""
        value = await self._client.get(self._PREFIX + session_id)
        if value is None:
            return None
        return int(value)

    async def delete(self, session_id: str) -> None:
        """Удаляет сессию (logout)"""
        await self._client.delete(self._PREFIX + session_id)
