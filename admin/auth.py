from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.db.postgres.base import AsyncSessionLocal
from app.db.postgres.repositories.user_repo import UserRepository
from app.db.redis_client import SessionStore, get_redis


class AdminAuth(AuthenticationBackend):
    """Проверяет сессию пользователя и флаг is_admin перед допуском в /admin"""

    async def login(self, request: Request) -> bool:
        """sqladmin вызывает этот метод при POST на /admin/login.

        Не используем собственную форму - пользователь должен войти через /api/v1/auth/login.
        """
        return False

    async def logout(self, request: Request) -> bool:
        return True

    async def authenticate(self, request: Request) -> bool:
        """Вызывается при каждом запросе к /admin/*.

        Читает session_id из cookie, проверяет Redis и флаг is_admin.
        """
        session_id = request.cookies.get("session_id")
        if not session_id:
            return False

        try:
            store = SessionStore(get_redis())
            user_id = await store.get_user_id(session_id)
            if user_id is None:
                return False

            async with AsyncSessionLocal() as session:
                repo = UserRepository(session)
                user = await repo.get_by_id(user_id)

            if user is None or not user.is_admin:
                return False

            return True
        except Exception:
            return False
