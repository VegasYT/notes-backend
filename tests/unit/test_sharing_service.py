import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError
from app.core.security import hash_password
from app.db.postgres.base import Base
from app.db.postgres.models import AccessLevel
from app.db.postgres.repositories.dashboard_repo import DashboardRepository
from app.db.postgres.repositories.user_repo import UserRepository
from app.services.sharing_service import SharingService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    """Тестовая сессия SQLite для unit-тестов шаринга"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        async with s.begin():
            yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def owner(session):
    """Создаёт пользователя-владельца"""
    repo = UserRepository(session)
    return await repo.create(email="owner@test.com", hashed_password=hash_password("pass"))


@pytest_asyncio.fixture
async def other_user(session):
    """Создаёт другого пользователя"""
    repo = UserRepository(session)
    return await repo.create(email="other@test.com", hashed_password=hash_password("pass"))


@pytest_asyncio.fixture
async def dashboard(session, owner):
    """Создаёт дашборд от имени владельца"""
    repo = DashboardRepository(session)
    return await repo.create(title="Test Dashboard", owner_id=owner.id)


@pytest.mark.asyncio
async def test_share_grants_access(session, owner, other_user, dashboard, mocker):
    """Шаринг создаёт запись доступа с указанным уровнем"""
    mocker.patch("app.services.sharing_service.send_event")

    service = SharingService(session)
    share = await service.share(
        dashboard_id=dashboard.id,
        target_user_id=other_user.id,
        access_level=AccessLevel.read,
        owner_id=owner.id,
    )

    assert share.dashboard_id == dashboard.id
    assert share.shared_with_user_id == other_user.id
    assert share.access_level == AccessLevel.read


@pytest.mark.asyncio
async def test_share_non_owner_raises_403(session, owner, other_user, dashboard, mocker):
    """Не-владелец не может расшарить дашборд"""
    mocker.patch("app.services.sharing_service.send_event")

    service = SharingService(session)

    with pytest.raises(ForbiddenError) as exc_info:
        await service.share(
            dashboard_id=dashboard.id,
            target_user_id=owner.id,
            access_level=AccessLevel.read,
            # other_user пытается расшарить чужой дашборд
            owner_id=other_user.id,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_share_duplicate_raises_409(session, owner, other_user, dashboard, mocker):
    """Повторный шаринг того же пользователя вызывает ConflictError"""
    mocker.patch("app.services.sharing_service.send_event")

    service = SharingService(session)
    await service.share(
        dashboard_id=dashboard.id,
        target_user_id=other_user.id,
        access_level=AccessLevel.read,
        owner_id=owner.id,
    )

    with pytest.raises(ConflictError) as exc_info:
        await service.share(
            dashboard_id=dashboard.id,
            target_user_id=other_user.id,
            access_level=AccessLevel.write,
            owner_id=owner.id,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_share_with_yourself_raises_400(session, owner, dashboard, mocker):
    """Нельзя расшарить дашборд самому себе - ожидается BadRequestError"""
    mocker.patch("app.services.sharing_service.send_event")

    service = SharingService(session)

    with pytest.raises(BadRequestError) as exc_info:
        await service.share(
            dashboard_id=dashboard.id,
            target_user_id=owner.id,
            access_level=AccessLevel.read,
            owner_id=owner.id,
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_revoke_removes_access(session, owner, other_user, dashboard, mocker):
    """Revoke удаляет запись доступа"""
    mocker.patch("app.services.sharing_service.send_event")

    service = SharingService(session)
    await service.share(
        dashboard_id=dashboard.id,
        target_user_id=other_user.id,
        access_level=AccessLevel.read,
        owner_id=owner.id,
    )

    await service.revoke(
        dashboard_id=dashboard.id,
        target_user_id=other_user.id,
        owner_id=owner.id,
    )

    # После отзыва - список доступов пуст
    shares = await service.list_shares(dashboard.id, owner.id)
    assert shares == []
