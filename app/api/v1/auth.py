from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_session
from app.db.postgres.models import User
from app.db.redis_client import SessionStore, get_redis
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Регистрирует нового пользователя и возвращает его данные"""
    service = AuthService(session, SessionStore(get_redis()))
    return await service.register(email=body.email, password=body.password)


@router.post("/login", response_model=UserResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Выполняет вход, устанавливает cookie с session_id и возвращает данные пользователя"""
    service = AuthService(session, SessionStore(get_redis()))
    session_id, user = await service.login(email=body.email, password=body.password)

    # Устанавливаем httponly cookie для безопасной передачи session_id
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
    )

    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Завершает сессию пользователя и удаляет cookie"""
    service = AuthService(session, SessionStore(get_redis()))
    await service.logout(session_id=session_id, user_id=current_user.id)
    response.delete_cookie("session_id")


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    """Возвращает данные текущего аутентифицированного пользователя"""
    return current_user
