from datetime import datetime, timezone

from sqladmin import BaseView, expose
from starlette.requests import Request

from app.db.mongo_client import get_mongo_db

_EVENT_TYPES = [
    "user.registered",
    "user.logged_in",
    "user.logged_out",
    "dashboard.created",
    "dashboard.deleted",
    "note.created",
    "note.updated",
    "note.deleted",
    "share.created",
    "share.deleted",
    "error.occurred",
]


class EventsView(BaseView):
    """Отображает события из MongoDB с фильтрацией и пагинацией"""

    name = "События"
    icon = "fa-solid fa-list"

    @expose("/events", methods=["GET"])
    async def events_page(self, request: Request):
        """Возвращает страницу с таблицей событий"""
        params = request.query_params

        page = max(1, int(params.get("page", 1)))
        per_page = max(1, min(200, int(params.get("per_page", 20))))
        sort_order = -1 if params.get("sort", "desc") == "desc" else 1
        event_type = params.get("event_type", "")
        user_id_raw = params.get("user_id", "").strip()
        date_from_raw = params.get("date_from", "").strip()
        date_to_raw = params.get("date_to", "").strip()

        mongo_filter: dict = {}

        if event_type:
            mongo_filter["event_type"] = event_type

        if user_id_raw:
            parts = [p.strip() for p in user_id_raw.split(",") if p.strip()]
            try:
                ids = [int(p) for p in parts]
            except ValueError:
                ids = parts
            mongo_filter["user_id"] = {"$in": ids} if len(ids) > 1 else ids[0]

        date_cond: dict = {}
        if date_from_raw:
            try:
                date_cond["$gte"] = datetime.fromisoformat(date_from_raw).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if date_to_raw:
            try:
                date_cond["$lte"] = datetime.fromisoformat(date_to_raw).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        if date_cond:
            mongo_filter["timestamp"] = date_cond

        db = get_mongo_db()
        total = await db["events"].count_documents(mongo_filter)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, total_pages)
        skip = (page - 1) * per_page

        cursor = db["events"].find(mongo_filter).sort("timestamp", sort_order).skip(skip).limit(per_page)
        events = await cursor.to_list(length=per_page)

        for event in events:
            event.pop("_id", None)

        return await self.templates.TemplateResponse(
            request,
            "events.html",
            {
                "events": events,
                "event_types": _EVENT_TYPES,
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "sort": "desc" if sort_order == -1 else "asc",
                "event_type": event_type,
                "user_id": user_id_raw,
                "date_from": date_from_raw,
                "date_to": date_to_raw,
            },
        )
