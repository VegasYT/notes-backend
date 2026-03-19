from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventRecord(BaseModel):
    """Запись события из MongoDB для отображения в admin-панели"""

    event_type: str
    user_id: int | None
    payload: dict[str, Any]
    timestamp: datetime
