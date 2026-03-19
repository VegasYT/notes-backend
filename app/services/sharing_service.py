import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.db.postgres.models import AccessLevel, DashboardShare
from app.db.postgres.repositories.dashboard_repo import DashboardRepository
from app.db.postgres.repositories.sharing_repo import SharingRepository
from app.db.postgres.repositories.user_repo import UserRepository
from app.kafka.events import AppEvent, EventType
from app.kafka.producer import send_event

logger = logging.getLogger(__name__)


class SharingService:
    """Сервис управления доступом к дашбордам

    Только владелец дашборда может выдавать и отзывать доступ
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SharingRepository(session)
        self._dashboard_repo = DashboardRepository(session)
        self._user_repo = UserRepository(session)

    async def share(
        self,
        dashboard_id: int,
        target_user_id: int,
        access_level: AccessLevel,
        owner_id: int,
    ) -> DashboardShare:
        """Выдаёт доступ к дашборду указанному пользователю"""
        dashboard = await self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id != owner_id:
            raise ForbiddenError("Only owner can share dashboard")

        target_user = await self._user_repo.get_by_id(target_user_id)
        if target_user is None:
            raise NotFoundError("Target user not found")

        if target_user_id == owner_id:
            raise BadRequestError("Cannot share with yourself")

        existing = await self._repo.get(dashboard_id, target_user_id)
        if existing:
            raise ConflictError("Access already granted")

        share = await self._repo.create(dashboard_id, target_user_id, access_level)
        logger.info(
            "Дашборд id=%d расшарен пользователю id=%d (уровень: %s)",
            dashboard_id, target_user_id, access_level.value,
        )

        await send_event(AppEvent(
            event_type=EventType.DASHBOARD_SHARED,
            user_id=owner_id,
            payload={
                "dashboard_id": dashboard_id,
                "shared_with": target_user_id,
                "access_level": access_level.value,
            },
        ))

        return share

    async def revoke(self, dashboard_id: int, target_user_id: int, owner_id: int) -> None:
        """Отзывает доступ к дашборду. Только владелец"""
        dashboard = await self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id != owner_id:
            raise ForbiddenError("Only owner can revoke access")

        share = await self._repo.get(dashboard_id, target_user_id)
        if share is None:
            raise NotFoundError("Share not found")

        await self._repo.delete(share)
        logger.info("Отозван доступ к дашборду id=%d для пользователя id=%d", dashboard_id, target_user_id)

    async def list_shares(self, dashboard_id: int, owner_id: int) -> list[DashboardShare]:
        """Возвращает список всех выданных доступов к дашборду"""
        dashboard = await self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id != owner_id:
            raise ForbiddenError("Only owner can view shares")

        return await self._repo.list_by_dashboard(dashboard_id)
