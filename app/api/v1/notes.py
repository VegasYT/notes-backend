from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.db.postgres.models import User
from app.schemas.note import NoteCreate, NoteResponse, NoteUpdate
from app.services.note_service import NoteService

router = APIRouter(prefix="/dashboards/{dashboard_id}/notes", tags=["Заметки"])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    dashboard_id: int,
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """Создаёт заметку в указанном дашборде"""
    return await NoteService(session).create(
        dashboard_id=dashboard_id,
        title=body.title,
        content=body.content,
        user_id=current_user.id,
    )


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[NoteResponse]:
    """Возвращает все заметки дашборда"""
    return await NoteService(session).list_by_dashboard(dashboard_id, current_user.id)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    dashboard_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """Возвращает заметку по id"""
    return await NoteService(session).get_or_403(note_id, current_user.id)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    dashboard_id: int,
    note_id: int,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> NoteResponse:
    """Частично обновляет заметку"""
    return await NoteService(session).update(note_id, body.title, body.content, current_user.id)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    dashboard_id: int,
    note_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Удаляет заметку"""
    await NoteService(session).delete(note_id, current_user.id)
