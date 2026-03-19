from datetime import datetime

from pydantic import BaseModel

from app.db.postgres.models import AccessLevel


class DashboardCreate(BaseModel):
    title: str


class DashboardUpdate(BaseModel):
    title: str


class DashboardResponse(BaseModel):
    id: int
    title: str
    owner_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareRequest(BaseModel):
    user_id: int
    access_level: AccessLevel = AccessLevel.read


class ShareResponse(BaseModel):
    id: int
    dashboard_id: int
    shared_with_user_id: int
    access_level: AccessLevel
    created_at: datetime

    model_config = {"from_attributes": True}
