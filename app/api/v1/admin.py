from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_admin_user, get_db_session
from app.db.mongo_client import get_mongo_db
from app.db.postgres.models import User
from app.db.postgres.repositories.user_repo import UserRepository
from app.schemas.admin import EventRecord
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Админка"])


@router.get("/events", response_model=list[EventRecord])
async def get_events(
    limit: int = Query(default=50, le=500),
    _admin: User = Depends(get_admin_user),
) -> list[EventRecord]:
    """Возвращает последние события из MongoDB (только администратор)"""
    db = get_mongo_db()
    cursor = db["events"].find().sort("timestamp", -1).limit(limit)
    events = await cursor.to_list(length=limit)

    for event in events:
        event.pop("_id", None)

    return events


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(get_admin_user),
) -> list[UserResponse]:
    """Возвращает список всех пользователей (только админ)"""
    return await UserRepository(session).list_all()


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(get_admin_user),
) -> None:
    """Удаляет пользователя по ID (только админ)"""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    await repo.delete(user)
