"""Эндпоинт /api/auth/verify для nginx auth_request.

Nginx проксирует каждый защищённый запрос сюда перед передачей в основное приложение.
200 - пользователь авторизован, 401 - не авторизован
"""

from fastapi import APIRouter, Cookie, Response, status

from app.db.redis_client import SessionStore, get_redis

router = APIRouter(tags=["Внтуренние"])


@router.get("/api/auth/verify")
async def verify_session(
    response: Response,
    session_id: str | None = Cookie(default=None),
) -> Response:
    """Проверяет валидность сессии из cookie"""
    if not session_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    store = SessionStore(get_redis())
    user_id = await store.get_user_id(session_id)

    if user_id is None:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return response

    response.status_code = status.HTTP_200_OK
    return response
