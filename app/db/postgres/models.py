import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres.base import Base


class AccessLevel(enum.Enum):
    """Уровень доступа к расшаренному дашборду"""

    read = "read"
    write = "write"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dashboards: Mapped[list["Dashboard"]] = relationship(
        "Dashboard", back_populates="owner", cascade="all, delete-orphan"
    )
    shared_accesses: Mapped[list["DashboardShare"]] = relationship(
        "DashboardShare", back_populates="shared_with", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"


class Dashboard(Base):
    """Доска заметок. Принадлежит одному владельцу, может быть расшарена другим пользователям"""

    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="dashboards")
    notes: Mapped[list["Note"]] = relationship(
        "Note", back_populates="dashboard", cascade="all, delete-orphan"
    )
    shares: Mapped[list["DashboardShare"]] = relationship(
        "DashboardShare", back_populates="dashboard", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Dashboard id={self.id} title={self.title!r}>"


class Note(Base):
    """Отдельная заметка, привязанная к дашборду"""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    dashboard_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="notes")

    def __repr__(self) -> str:
        return f"<Note id={self.id} title={self.title!r}>"


class DashboardShare(Base):
    """Выданный доступ к дашборду другому пользователю"""

    __tablename__ = "dashboard_shares"
    __table_args__ = (
        UniqueConstraint("dashboard_id", "shared_with_user_id", name="uq_dashboard_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dashboard_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shared_with_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel), nullable=False, default=AccessLevel.read
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dashboard: Mapped["Dashboard"] = relationship("Dashboard", back_populates="shares")
    shared_with: Mapped["User"] = relationship("User", back_populates="shared_accesses")

    def __repr__(self) -> str:
        return (
            f"<DashboardShare dashboard={self.dashboard_id} "
            f"user={self.shared_with_user_id} level={self.access_level}>"
        )
