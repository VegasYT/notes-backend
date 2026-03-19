import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import verify_password
from app.db.postgres.base import Base
from app.db.postgres.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    """Тестовая сессия SQLite для unit-тестов"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        async with s.begin():
            yield s

    await engine.dispose()


class FakeSessionStore:
    """Фейковый SessionStore - хранит сессии в памяти"""

    def __init__(self):
        self._data: dict[str, int] = {}

    async def create(self, user_id: int) -> str:
        session_id = f"fake-session-{user_id}"
        self._data[session_id] = user_id
        return session_id

    async def get_user_id(self, session_id: str) -> int | None:
        return self._data.get(session_id)

    async def delete(self, session_id: str) -> None:
        self._data.pop(session_id, None)


@pytest.mark.asyncio
async def test_register_creates_user(session, mocker):
    """Регистрация создаёт пользователя с захэшированным паролем"""
    mocker.patch("app.services.auth_service.send_event")

    service = AuthService(session, FakeSessionStore())
    user = await service.register(email="test@example.com", password="secret123")

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.hashed_password != "secret123"
    assert verify_password("secret123", user.hashed_password)


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_409(session, mocker):
    mocker.patch("app.services.auth_service.send_event")

    service = AuthService(session, FakeSessionStore())
    await service.register(email="dup@example.com", password="pass1")

    with pytest.raises(ConflictError) as exc_info:
        await service.register(email="dup@example.com", password="pass2")

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_session_id(session, mocker):
    mocker.patch("app.services.auth_service.send_event")

    store = FakeSessionStore()
    service = AuthService(session, store)
    await service.register(email="login@example.com", password="mypassword")

    session_id = await service.login(email="login@example.com", password="mypassword")
    assert session_id is not None
    assert await store.get_user_id(session_id) is not None


@pytest.mark.asyncio
async def test_login_wrong_password_raises_401(session, mocker):
    mocker.patch("app.services.auth_service.send_event")

    service = AuthService(session, FakeSessionStore())
    await service.register(email="wrong@example.com", password="correct")

    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login(email="wrong@example.com", password="incorrect")

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_removes_session(session, mocker):
    mocker.patch("app.services.auth_service.send_event")

    store = FakeSessionStore()
    service = AuthService(session, store)
    await service.register(email="logout@example.com", password="pass")
    session_id = await service.login(email="logout@example.com", password="pass")

    # До логаута - сессия активна
    assert await store.get_user_id(session_id) is not None

    user_id = await store.get_user_id(session_id)
    await service.logout(session_id=session_id, user_id=user_id)

    # После логаута - сессия удалена
    assert await store.get_user_id(session_id) is None
