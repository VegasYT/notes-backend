from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.db.postgres.models import User
from app.schemas.dashboard import ShareRequest, ShareResponse
from app.services.sharing_service import SharingService

router = APIRouter(prefix="/dashboards/{dashboard_id}/shares", tags=["Поделиться досутпом"])


@router.post("", response_model=ShareResponse, status_code=status.HTTP_201_CREATED)
async def share_dashboard(
    dashboard_id: int,
    body: ShareRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ShareResponse:
    """Выдаёт доступ к дашборду указанному пользователю (только владелец)"""
    return await SharingService(session).share(
        dashboard_id=dashboard_id,
        target_user_id=body.user_id,
        access_level=body.access_level,
        owner_id=current_user.id,
    )


@router.get("", response_model=list[ShareResponse])
async def list_shares(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[ShareResponse]:
    """Возвращает список всех выданных доступов (только владелец)"""
    return await SharingService(session).list_shares(dashboard_id, current_user.id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share(
    dashboard_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Отзывает доступ у указанного пользователя (только владелец)"""
    await SharingService(session).revoke(
        dashboard_id=dashboard_id,
        target_user_id=user_id,
        owner_id=current_user.id,
    )
