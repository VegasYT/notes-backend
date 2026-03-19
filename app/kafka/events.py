from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Типы событий системы"""

    USER_REGISTERED = "user.registered"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    DASHBOARD_CREATED = "dashboard.created"
    DASHBOARD_UPDATED = "dashboard.updated"
    DASHBOARD_DELETED = "dashboard.deleted"
    DASHBOARD_SHARED = "dashboard.shared"
    NOTE_CREATED = "note.created"
    NOTE_UPDATED = "note.updated"
    NOTE_DELETED = "note.deleted"
    ERROR_OCCURRED = "error.occurred"


class AppEvent(BaseModel):
    """Базовая структура события для отправки в Kafka и хранения в MongoDB"""

    event_type: EventType
    user_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
