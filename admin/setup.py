from sqladmin import Admin, ModelView

from admin.auth import AdminAuth
from admin.events_view import EventsView
from app.db.postgres.base import engine
from app.db.postgres.models import Dashboard, DashboardShare, Note, User


class UserAdmin(ModelView, model=User):
    """Управление пользователями.

    Показывает основные поля, скрывает хэш пароля.
    Позволяет удалять пользователей.
    """

    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"

    column_list = [User.id, User.email, User.is_admin, User.created_at]
    column_searchable_list = [User.email]
    column_sortable_list = [User.id, User.created_at]

    # Запрещаем создание и редактирование через admin - только просмотр и удаление
    can_create = False
    can_edit = False
    can_delete = True


class DashboardAdmin(ModelView, model=Dashboard):
    """Просмотр дашбордов в admin-интерфейсе"""

    name = "Дашборд"
    name_plural = "Дашборды"
    icon = "fa-solid fa-table-columns"

    column_list = [Dashboard.id, Dashboard.title, Dashboard.owner_id, Dashboard.created_at]
    column_sortable_list = [Dashboard.id, Dashboard.created_at]

    can_create = False
    can_edit = False
    can_delete = True


class NoteAdmin(ModelView, model=Note):
    """Просмотр заметок в admin-интерфейсе"""

    name = "Заметка"
    name_plural = "Заметки"
    icon = "fa-solid fa-note-sticky"

    column_list = [Note.id, Note.title, Note.dashboard_id, Note.created_at]
    column_sortable_list = [Note.id, Note.created_at]

    can_create = False
    can_edit = False
    can_delete = True


class DashboardShareAdmin(ModelView, model=DashboardShare):
    """Просмотр выданных доступов к дашбордам"""

    name = "Доступ"
    name_plural = "Доступы"
    icon = "fa-solid fa-share-nodes"

    column_list = [
        DashboardShare.id,
        DashboardShare.dashboard_id,
        DashboardShare.shared_with_user_id,
        DashboardShare.access_level,
        DashboardShare.created_at,
    ]

    can_create = False
    can_edit = False
    can_delete = True


def create_admin(app) -> Admin:
    """Создаёт и настраивает экземпляр sqladmin, регистрирует все ModelView"""
    admin = Admin(
        app,
        engine,
        title="Notes Admin",
        authentication_backend=AdminAuth(secret_key="admin"),
        templates_dir="templates/sqladmin",
    )
    admin.add_view(UserAdmin)
    admin.add_view(DashboardAdmin)
    admin.add_view(NoteAdmin)
    admin.add_view(DashboardShareAdmin)
    admin.add_base_view(EventsView)
    return admin
