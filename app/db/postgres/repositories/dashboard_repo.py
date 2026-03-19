from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import Dashboard, DashboardShare


class DashboardRepository:
    """Инкапсулирует все запросы к БД для сущности Dashboard"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, title: str, owner_id: int) -> Dashboard:
        """Создаёт и сохраняет новый дашборд"""
        dashboard = Dashboard(title=title, owner_id=owner_id)
        self._session.add(dashboard)
        await self._session.flush()
        await self._session.refresh(dashboard)
        return dashboard

    async def get_by_id(self, dashboard_id: int) -> Dashboard | None:
        """Возвращает дашборд по первичному ключу или None"""
        result = await self._session.execute(
            select(Dashboard).where(Dashboard.id == dashboard_id)
        )
        return result.scalar_one_or_none()

    async def list_accessible(self, user_id: int) -> list[Dashboard]:
        """Возвращает дашборды, которые пользователь создал или в которые получил доступ"""
        result = await self._session.execute(
            select(Dashboard)
            .outerjoin(DashboardShare, DashboardShare.dashboard_id == Dashboard.id)
            .where(
                or_(
                    Dashboard.owner_id == user_id,
                    DashboardShare.shared_with_user_id == user_id,
                )
            )
            .distinct()
            .order_by(Dashboard.id)
        )
        return list(result.scalars().all())

    async def update(self, dashboard: Dashboard, title: str) -> Dashboard:
        """Обновляет название дашборда"""
        dashboard.title = title
        await self._session.flush()
        await self._session.refresh(dashboard)
        return dashboard

    async def delete(self, dashboard: Dashboard) -> None:
        """Удаляет дашборд с каскадным удалением заметок и записей шаринга"""
        await self._session.delete(dashboard)
        await self._session.flush()
