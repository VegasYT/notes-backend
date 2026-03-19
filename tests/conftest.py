import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.postgres.base import Base
from app.db.postgres.models import User
from app.db.redis_client import SessionStore

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_engine():
    """Создаёт тестовый движок SQLite и все таблицы"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    """Открывает тестовую сессию БД с откатом после каждого теста"""
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def mock_redis(mocker):
    """Мок Redis: имитирует SessionStore без реального подключения"""
    store = mocker.AsyncMock(spec=SessionStore)
    mocker.patch("app.api.v1.auth.get_redis", return_value=mocker.MagicMock())
    mocker.patch("app.core.dependencies.get_redis", return_value=mocker.MagicMock())
    return store


@pytest.fixture
def mock_kafka(mocker):
    """Мок Kafka producer - события уходят в /dev/null"""
    return mocker.patch("app.kafka.producer.send_event", return_value=None)
