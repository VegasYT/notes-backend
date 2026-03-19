from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import User


class UserRepository:
    """Инкапсулирует все запросы к БД для сущности User"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, email: str, hashed_password: str) -> User:
        """Сохраняет нового пользователя и возвращает его"""
        user = User(email=email, hashed_password=hashed_password)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по первичному ключу или none"""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Возвращает пользователя по email или None"""
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[User]:
        """Возвращает всех пользователей (используется в admin)"""
        result = await self._session.execute(select(User).order_by(User.id))
        return list(result.scalars().all())

    async def delete(self, user: User) -> None:
        """Удаляет пользователя из БД"""
        await self._session.delete(user)
        await self._session.flush()
