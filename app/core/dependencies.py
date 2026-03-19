from typing import AsyncGenerator

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.base import AsyncSessionLocal
from app.db.postgres.models import User
from app.db.postgres.repositories.user_repo import UserRepository
from app.db.redis_client import SessionStore, get_redis


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


async def get_current_user(
    session_id: str | None = Cookie(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Возвращает текущего аутентифицированного пользователя.

    Читает session_id из cookie, проверяет Redis, загружает User из PostgreSQL.
    Выбрасывает 401, если сессия отсутствует или невалидна
    """
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    store = SessionStore(get_redis())
    user_id = await store.get_user_id(session_id)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return user


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
