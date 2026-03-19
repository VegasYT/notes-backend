import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.postgres.models import AccessLevel, Dashboard
from app.db.postgres.repositories.dashboard_repo import DashboardRepository
from app.db.postgres.repositories.sharing_repo import SharingRepository
from app.kafka.events import AppEvent, EventType
from app.kafka.producer import send_event

logger = logging.getLogger(__name__)


class DashboardService:
    """Сервис CRUD-операций над дашбордами с проверкой прав доступа"""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = DashboardRepository(session)
        self._sharing_repo = SharingRepository(session)

    async def create(self, title: str, owner_id: int) -> Dashboard:
        dashboard = await self._repo.create(title=title, owner_id=owner_id)
        logger.info("Создан дашборд id=%d owner=%d", dashboard.id, owner_id)

        await send_event(AppEvent(
            event_type=EventType.DASHBOARD_CREATED,
            user_id=owner_id,
            payload={"dashboard_id": dashboard.id, "title": title},
        ))

        return dashboard

    async def list_for_user(self, user_id: int) -> list[Dashboard]:
        """Возвращает дашборды, доступные пользователю (свои + расшаренные)"""
        return await self._repo.list_accessible(user_id)

    async def get_or_403(self, dashboard_id: int, user_id: int) -> Dashboard:
        """Возвращает дашборд, если пользователь имеет к нему доступ"""
        dashboard = await self._repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id == user_id:
            return dashboard

        share = await self._sharing_repo.get(dashboard_id, user_id)
        if share is None:
            raise ForbiddenError("Access denied")

        return dashboard

    async def update(self, dashboard_id: int, title: str, user_id: int) -> Dashboard:
        """Обновляет дашборд. Только владелец или пользователь с уровнем write"""
        dashboard = await self._repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        await self._check_write_access(dashboard, user_id)

        updated = await self._repo.update(dashboard, title)
        logger.info("Обновлён дашборд id=%d", dashboard_id)

        await send_event(AppEvent(
            event_type=EventType.DASHBOARD_UPDATED,
            user_id=user_id,
            payload={"dashboard_id": dashboard_id, "title": title},
        ))

        return updated

    async def delete(self, dashboard_id: int, user_id: int) -> None:
        """Удаляет дашборд. Только владелец"""
        dashboard = await self._repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id != user_id:
            raise ForbiddenError("Only owner can delete")

        await self._repo.delete(dashboard)
        logger.info("Удалён дашборд id=%d", dashboard_id)

        await send_event(AppEvent(
            event_type=EventType.DASHBOARD_DELETED,
            user_id=user_id,
            payload={"dashboard_id": dashboard_id},
        ))

    async def _check_write_access(self, dashboard: Dashboard, user_id: int) -> None:
        """Проверяет, что пользователь может редактировать дашборд"""
        if dashboard.owner_id == user_id:
            return

        share = await self._sharing_repo.get(dashboard.id, user_id)
        if share is None or share.access_level != AccessLevel.write:
            raise ForbiddenError("Write access required")
