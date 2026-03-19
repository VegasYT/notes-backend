import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.postgres.models import AccessLevel, Note
from app.db.postgres.repositories.dashboard_repo import DashboardRepository
from app.db.postgres.repositories.note_repo import NoteRepository
from app.db.postgres.repositories.sharing_repo import SharingRepository
from app.kafka.events import AppEvent, EventType
from app.kafka.producer import send_event

logger = logging.getLogger(__name__)


class NoteService:
    """Сервис CRUD-операций над заметками с проверкой прав доступа через дашборд"""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = NoteRepository(session)
        self._dashboard_repo = DashboardRepository(session)
        self._sharing_repo = SharingRepository(session)

    async def _get_dashboard_or_403(self, dashboard_id: int, user_id: int, write: bool = False):
        """Проверяет доступ пользователя к дашборду

        Аргумент write=True требует уровня write для не-владельцев.
        """
        dashboard = await self._dashboard_repo.get_by_id(dashboard_id)
        if dashboard is None:
            raise NotFoundError("Dashboard not found")

        if dashboard.owner_id == user_id:
            return dashboard

        share = await self._sharing_repo.get(dashboard_id, user_id)
        if share is None:
            raise ForbiddenError("Access denied")

        if write and share.access_level != AccessLevel.write:
            raise ForbiddenError("Write access required")

        return dashboard

    async def create(self, dashboard_id: int, title: str, content: str, user_id: int) -> Note:
        """Создаёт заметку в указанном дашборде"""
        await self._get_dashboard_or_403(dashboard_id, user_id, write=True)

        note = await self._repo.create(title=title, content=content, dashboard_id=dashboard_id)
        logger.info("Создана заметка id=%d в дашборде id=%d", note.id, dashboard_id)

        await send_event(AppEvent(
            event_type=EventType.NOTE_CREATED,
            user_id=user_id,
            payload={"note_id": note.id, "dashboard_id": dashboard_id},
        ))

        return note

    async def list_by_dashboard(self, dashboard_id: int, user_id: int) -> list[Note]:
        """Возвращает все заметки дашборда (требует наличие любого уровня доступа)"""
        await self._get_dashboard_or_403(dashboard_id, user_id)
        return await self._repo.list_by_dashboard(dashboard_id)

    async def get_or_403(self, note_id: int, user_id: int) -> Note:
        """Возвращает заметку, проверяя доступ к родительскому дашборду"""
        note = await self._repo.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Note not found")

        await self._get_dashboard_or_403(note.dashboard_id, user_id)
        return note

    async def update(
        self, note_id: int, title: str | None, content: str | None, user_id: int
    ) -> Note:
        """Обновляет заметку. Требует write доступ к дашборду"""
        note = await self._repo.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Note not found")

        await self._get_dashboard_or_403(note.dashboard_id, user_id, write=True)

        updated = await self._repo.update(note, title, content)
        logger.info("Обновлена заметка id=%d", note_id)

        await send_event(AppEvent(
            event_type=EventType.NOTE_UPDATED,
            user_id=user_id,
            payload={"note_id": note_id},
        ))

        return updated

    async def delete(self, note_id: int, user_id: int) -> None:
        """Удаляет заметку. Требует write доступ к дашборду"""
        note = await self._repo.get_by_id(note_id)
        if note is None:
            raise NotFoundError("Note not found")

        await self._get_dashboard_or_403(note.dashboard_id, user_id, write=True)

        await self._repo.delete(note)
        logger.info("Удалена заметка id=%d", note_id)

        await send_event(AppEvent(
            event_type=EventType.NOTE_DELETED,
            user_id=user_id,
            payload={"note_id": note_id},
        ))
