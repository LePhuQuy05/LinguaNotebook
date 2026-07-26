"""Schedule service — CRUD operations for study schedules."""

import logging
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.schedule import Schedule

logger = logging.getLogger(__name__)


async def create_schedule(
    db: AsyncSession,
    user_id: str,
    name: str,
    days_of_week: list[int],
    time_of_day: str,
    duration_minutes: int,
    content_types: list[str],
    daily_item_count: int = 10,
) -> Schedule:
    """Create a new study schedule."""
    _validate_schedule(days_of_week, duration_minutes, content_types, daily_item_count)

    hour, minute = map(int, time_of_day.split(":"))
    schedule = Schedule(
        user_id=user_id,
        name=name,
        days_of_week=days_of_week,
        time_of_day=time(hour, minute),
        duration_minutes=duration_minutes,
        content_types=content_types,
        daily_item_count=daily_item_count,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)
    return schedule


async def get_schedules(db: AsyncSession, user_id: str) -> list[Schedule]:
    """List all schedules for a user."""
    result = await db.execute(
        select(Schedule).where(Schedule.user_id == user_id).order_by(Schedule.created_at)
    )
    return list(result.scalars().all())


async def update_schedule(
    db: AsyncSession, schedule_id: str, user_id: str, **kwargs
) -> Schedule | None:
    """Update a schedule's fields."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return None

    if "time_of_day" in kwargs and isinstance(kwargs["time_of_day"], str):
        h, m = map(int, kwargs["time_of_day"].split(":"))
        kwargs["time_of_day"] = time(h, m)

    for key, value in kwargs.items():
        if hasattr(schedule, key) and value is not None:
            setattr(schedule, key, value)

    await db.commit()
    await db.refresh(schedule)
    return schedule


async def delete_schedule(db: AsyncSession, schedule_id: str, user_id: str) -> bool:
    """Delete a schedule."""
    result = await db.execute(
        select(Schedule).where(Schedule.id == schedule_id, Schedule.user_id == user_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return False
    await db.delete(schedule)
    await db.commit()
    return True


def _validate_schedule(days: list[int], duration: int, content_types: list[str], item_count: int):
    """Validate schedule parameters."""
    if not days or not all(1 <= d <= 7 for d in days):
        raise ValueError("days_of_week must be integers 1-7")
    if not 5 <= duration <= 120:
        raise ValueError("duration_minutes must be 5-120")
    valid_types = {"vocabulary", "reading", "grammar", "listening"}
    if not content_types or not set(content_types).issubset(valid_types):
        raise ValueError(f"content_types must be subset of {valid_types}")
    if not 5 <= item_count <= 50:
        raise ValueError("daily_item_count must be 5-50")
