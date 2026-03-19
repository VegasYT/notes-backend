from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db_session
from app.db.mongo_client import get_mongo_db
from app.db.postgres.models import User
from app.schemas.admin import EventRecord
from app.schemas.auth import UserResponse
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["Админка"])


@router.get("/events", response_model=list[EventRecord])
async def get_events(
    limit: int = Query(default=50, le=500),
    _admin: User = Depends(get_admin_user),
) -> list[EventRecord]:
    """Возвращает последние события из MongoDB (только админ)"""
    return await AdminService(mongo_db=get_mongo_db()).get_events(limit)


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_admin_user),
) -> list[UserResponse]:
    """Возвращает список всех пользователей (только админ)"""
    return await AdminService(session=session).list_users()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_admin_user),
) -> None:
    """Удаляет пользователя по ID (только админ)"""
    await AdminService(session=session).delete_user(user_id, admin.id)
