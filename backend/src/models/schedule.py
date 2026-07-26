"""Schedule ORM model — user-defined recurring study plans."""

import enum
import uuid
from datetime import datetime, time, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class ContentType(str, enum.Enum):
    vocabulary = "vocabulary"
    reading = "reading"
    grammar = "grammar"
    listening = "listening"


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    days_of_week: Mapped[list] = mapped_column(JSON, nullable=False)
    time_of_day: Mapped[time] = mapped_column(Time, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_types: Mapped[list] = mapped_column(JSON, nullable=False)
    daily_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
