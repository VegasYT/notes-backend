from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.db.postgres.models import User
from app.schemas.dashboard import DashboardCreate, DashboardResponse, DashboardUpdate
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboards", tags=["Панели заметок"])


@router.post("", response_model=DashboardResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard(
    body: DashboardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardResponse:
    """Создаёт новый дашборд для текущего пользователя"""
    return await DashboardService(session).create(title=body.title, owner_id=current_user.id)


@router.get("", response_model=list[DashboardResponse])
async def list_dashboards(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DashboardResponse]:
    """Возвращает дашборды, доступные текущему пользователю"""
    return await DashboardService(session).list_for_user(current_user.id)


@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardResponse:
    """Возвращает дашборд по ID (требует наличие доступа)"""
    return await DashboardService(session).get_or_403(dashboard_id, current_user.id)


@router.put("/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: int,
    body: DashboardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardResponse:
    """Обновляет название дашборда (владелец или write-доступ)"""
    return await DashboardService(session).update(dashboard_id, body.title, current_user.id)


@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Удаляет дашборд (только владелец)"""
    await DashboardService(session).delete(dashboard_id, current_user.id)
