from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import Note


class NoteRepository:
    """Инкапсулирует все запросы к БД для сущности Note"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, title: str, content: str, dashboard_id: int) -> Note:
        """Создаёт и сохраняет новую заметку"""
        note = Note(title=title, content=content, dashboard_id=dashboard_id)
        self._session.add(note)
        await self._session.flush()
        await self._session.refresh(note)
        return note

    async def get_by_id(self, note_id: int) -> Note | None:
        """Возвращает заметку по первичному ключу или None"""
        result = await self._session.execute(select(Note).where(Note.id == note_id))
        return result.scalar_one_or_none()

    async def list_by_dashboard(self, dashboard_id: int) -> list[Note]:
        """Возвращает все заметки указанного дашборда"""
        result = await self._session.execute(
            select(Note).where(Note.dashboard_id == dashboard_id).order_by(Note.id)
        )
        return list(result.scalars().all())

    async def update(self, note: Note, title: str | None, content: str | None) -> Note:
        """Обновляет поля заметки (обновляет только переданные значения)"""
        if title is not None:
            note.title = title
        if content is not None:
            note.content = content
        await self._session.flush()
        await self._session.refresh(note)
        return note

    async def delete(self, note: Note) -> None:
        """Удаляет заметку"""
        await self._session.delete(note)
        await self._session.flush()
