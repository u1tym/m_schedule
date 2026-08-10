from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ActivityCategory(Base):
    __tablename__ = "activity_categories"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    schedules: Mapped[list["Schedule"]] = relationship(back_populates="activity_category")


class Holiday(Base):
    __tablename__ = "holidays"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RoutineAdaptDay(Base):
    """plan.routine_adapt_day（routine.adapt_id 参照用。他カラムは未マップ）。"""

    __tablename__ = "routine_adapt_day"
    __table_args__ = {"schema": "plan"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class RoutineAdjustDay(Base):
    """plan.routine_adjust_day（routine.adjust_id 参照用。他カラムは未マップ）。"""

    __tablename__ = "routine_adjust_day"
    __table_args__ = {"schema": "plan"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Routine(Base):
    """plan.routine（DB と整合。本 API は主に schedules.routine_id 経由の参照）。"""

    __tablename__ = "routine"
    __table_args__ = (
        UniqueConstraint("title", name="uq_routine_title"),
        {"schema": "plan"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    activity_category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calendar.activity_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adapt_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("plan.routine_adapt_day.id", ondelete="RESTRICT"),
        nullable=False,
    )
    adjust_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("plan.routine_adjust_day.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Schedule(Base):
    __tablename__ = "schedules"
    __table_args__ = {"schema": "calendar"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    is_all_day: Mapped[bool] = mapped_column(Boolean, nullable=False)
    activity_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("calendar.activity_categories.id"), nullable=False
    )
    schedule_type: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_todo_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    routine_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("plan.routine.id", ondelete="SET NULL"),
        nullable=True,
    )
    notified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    aid: Mapped[int | None] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=True)
    emailed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    activity_category: Mapped[ActivityCategory] = relationship(back_populates="schedules")
