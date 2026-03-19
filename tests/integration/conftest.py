import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.postgres.base import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_app(mocker):
    """Создаёт тестовое FastAPI приложение с подменёнными зависимостями"""
    # Создаём тестовый движок
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Хранилище сессий в памяти вместо Redis
    fake_sessions: dict[str, int] = {}

    class FakeSessionStore:
        async def create(self, user_id: int) -> str:
            import uuid
            sid = str(uuid.uuid4())
            fake_sessions[sid] = user_id
            return sid

        async def get_user_id(self, session_id: str) -> int | None:
            return fake_sessions.get(session_id)

        async def delete(self, session_id: str) -> None:
            fake_sessions.pop(session_id, None)

    fake_store = FakeSessionStore()

    # Подменяем get_redis
    mock_redis = mocker.MagicMock()
    mocker.patch("app.db.redis_client.redis_pool", mock_redis)
    mocker.patch("app.db.redis_client.get_redis", return_value=mock_redis)

    # Подменяем SessionStore везде
    mocker.patch("app.api.v1.auth.SessionStore", return_value=fake_store)
    mocker.patch("app.core.dependencies.SessionStore", return_value=fake_store)

    # Мокаем Kafka
    mocker.patch("app.kafka.producer.send_event")
    mocker.patch("app.kafka.producer._producer", mocker.MagicMock())

    # Подменяем сессию БД
    async def override_db():
        async with test_session_factory() as session:
            async with session.begin():
                yield session

    from app.core.dependencies import get_db_session
    from app.main import create_app
    application = create_app()
    application.dependency_overrides[get_db_session] = override_db

    # Отключаем lifespan (Redis/Mongo/Kafka не нужны в тестах)
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def noop_lifespan(app):
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield

    application.router.lifespan_context = noop_lifespan

    yield application, fake_store, fake_sessions

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(test_app):
    """HTTP-клиент для тестовых запросов"""
    app, store, sessions = test_app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c, store, sessions
