from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import AccessLevel, DashboardShare


class SharingRepository:
    """Инкапсулирует запросы к БД для управления доступом к дашбордам"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        dashboard_id: int,
        shared_with_user_id: int,
        access_level: AccessLevel,
    ) -> DashboardShare:
        """Создаёт запись о выданном доступе"""
        share = DashboardShare(
            dashboard_id=dashboard_id,
            shared_with_user_id=shared_with_user_id,
            access_level=access_level,
        )
        self._session.add(share)
        await self._session.flush()
        await self._session.refresh(share)
        return share

    async def get(self, dashboard_id: int, user_id: int) -> DashboardShare | None:
        """Возвращает запись доступа для конкретного пользователя и дашборда"""
        result = await self._session.execute(
            select(DashboardShare).where(
                DashboardShare.dashboard_id == dashboard_id,
                DashboardShare.shared_with_user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_dashboard(self, dashboard_id: int) -> list[DashboardShare]:
        """Возвращает все записи доступа для указанного дашборда"""
        result = await self._session.execute(
            select(DashboardShare).where(DashboardShare.dashboard_id == dashboard_id)
        )
        return list(result.scalars().all())

    async def delete(self, share: DashboardShare) -> None:
        """Отзывает доступ - удаляет запись шаринга"""
        await self._session.delete(share)
        await self._session.flush()
