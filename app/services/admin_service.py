from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import User
from app.db.postgres.repositories.user_repo import UserRepository


class AdminService:
    def __init__(
        self,
        session: AsyncSession | None = None,
        mongo_db: AsyncIOMotorDatabase | None = None,
    ) -> None:
        self._session = session
        self._mongo_db = mongo_db

    async def get_events(self, limit: int) -> list[dict]:
        cursor = self._mongo_db["events"].find().sort("timestamp", -1).limit(limit)
        events = await cursor.to_list(length=limit)
        for event in events:
            event.pop("_id", None)
        return events

    async def list_users(self) -> list[User]:
        return await UserRepository(self._session).list_all()

    async def delete_user(self, user_id: int, admin_id: int) -> None:
        repo = UserRepository(self._session)
        user = await repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if user.id == admin_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
        await repo.delete(user)
