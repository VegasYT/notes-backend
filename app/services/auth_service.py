import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.db.postgres.models import User
from app.db.postgres.repositories.user_repo import UserRepository
from app.db.redis_client import SessionStore
from app.kafka.events import AppEvent, EventType
from app.kafka.producer import send_event

logger = logging.getLogger(__name__)


class AuthService:
    """Сервис регистрации, входа и выхода пользователей"""

    def __init__(self, session: AsyncSession, store: SessionStore) -> None:
        self._repo = UserRepository(session)
        self._store = store

    async def register(self, email: str, password: str) -> User:
        existing = await self._repo.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")

        user = await self._repo.create(
            email=email,
            hashed_password=hash_password(password),
        )
        logger.info("Зарегистрирован новый пользователь: %s", email)

        await send_event(AppEvent(
            event_type=EventType.USER_REGISTERED,
            user_id=user.id,
            payload={"email": email},
        ))

        return user

    async def login(self, email: str, password: str) -> tuple[str, User]:
        """Проверяет учётные данные и создаёт сессию в Redis"""
        user = await self._repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid credentials")

        session_id = await self._store.create(user.id)
        logger.info("Пользователь вошёл в систему: %s", email)

        await send_event(AppEvent(
            event_type=EventType.USER_LOGGED_IN,
            user_id=user.id,
            payload={"email": email},
        ))

        return session_id, user

    async def logout(self, session_id: str, user_id: int) -> None:
        """Удаляет сессию из Redis"""
        await self._store.delete(session_id)
        logger.info("Пользователь вышел из системы: user_id=%d", user_id)

        await send_event(AppEvent(
            event_type=EventType.USER_LOGGED_OUT,
            user_id=user_id,
            payload={},
        ))
