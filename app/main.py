import logging
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from admin.setup import create_admin
from app.api.auth_check import router as auth_check_router
from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboards import router as dashboards_router
from app.api.v1.notes import router as notes_router
from app.api.v1.sharing import router as sharing_router
from app.core.exceptions import BaseAppException
from app.core.telegram import notify_error
from app.db.mongo_client import close_mongo, init_mongo
from app.db.postgres.base import engine
from app.db.redis_client import close_redis, init_redis
from app.kafka.consumer import start_consumer, stop_consumer
from app.kafka.events import AppEvent, EventType
from app.kafka.producer import init_producer, send_event, stop_producer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """
    При старте: инициализирует Redis / MongoDB / Kafka.
    При завершении: корректно закрывает все соединения.
    """
    await init_redis()
    await init_mongo()
    await init_producer()
    await start_consumer()

    yield

    await stop_consumer()
    await stop_producer()
    await close_mongo()
    await close_redis()
    await engine.dispose()


async def app_middleware(request: Request, call_next) -> Response:
    """Перехватывает доменные исключения и конвертирует их в JSON-ответы"""
    try:
        return await call_next(request)
    except BaseAppException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"detail": e.detail},
        )
    except Exception as e:
        logger.exception("InternalServerError")

        # Пытаемся получить user_id из сессии для обогащения лога
        user_id = None
        try:
            session_id = request.cookies.get("session_id")
            if session_id:
                from app.db.redis_client import SessionStore, get_redis
                user_id = await SessionStore(get_redis()).get_user_id(session_id)
        except Exception:
            pass

        tb = traceback.format_exc()

        await notify_error(
            path=str(request.url.path),
            method=request.method,
            error=str(e),
            tb=tb,
        )
        await send_event(AppEvent(
            event_type=EventType.ERROR_OCCURRED,
            user_id=user_id,
            payload={
                "path": str(request.url.path),
                "method": request.method,
                "error": str(e),
                "traceback": tb,
            },
        ))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )


def create_app() -> FastAPI:
    application = FastAPI(
        title="Notes Management API",
        description="Backend для системы управления заметками",
        lifespan=lifespan,
        docs_url="/joqendo32jr923JIDWd2wkdw4",
        redoc_url=None,
    )

    application.middleware("http")(app_middleware)

    # Внутренний эндпоинт для Nginx auth_request
    application.include_router(auth_check_router)

    # API v1
    api_prefix = "/api/v1"
    application.include_router(auth_router, prefix=api_prefix)
    application.include_router(dashboards_router, prefix=api_prefix)
    application.include_router(notes_router, prefix=api_prefix)
    application.include_router(sharing_router, prefix=api_prefix)
    application.include_router(admin_router, prefix=api_prefix)

    # sqladmin - монтируется на /admin
    create_admin(application)

    return application


app = create_app()
