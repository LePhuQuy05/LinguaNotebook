"""Offline sync service — push/pull changes with LWW conflict resolution."""

import hashlib
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sync import SyncLog, SyncAction

logger = logging.getLogger(__name__)
MAX_BATCH_SIZE = 500


async def push_changes(
    db: AsyncSession,
    user_id: str,
    device_id: str,
    changes: list[dict],
) -> dict:
    """Push offline changes to server. Returns {accepted, conflicts}."""
    accepted = 0
    conflicts = []

    for change in changes[:MAX_BATCH_SIZE]:
        entity_type = change.get("entity_type")
        entity_id = change.get("entity_id")
        action = change.get("action")
        client_timestamp = change.get("client_timestamp")
        payload_hash = change.get("payload_hash", "")

        # Check for conflicts: has this entity been modified since last sync?
        result = await db.execute(
            select(SyncLog).where(
                SyncLog.entity_id == entity_id,
                SyncLog.synced_at > datetime.fromisoformat(client_timestamp.replace("Z", "+00:00")),
            ).order_by(SyncLog.synced_at.desc()).limit(1)
        )
        last_sync = result.scalar_one_or_none()

        if last_sync:
            # Conflict: server version is newer → LWW: server wins
            conflicts.append({
                "entity_id": entity_id,
                "resolution": "server_win",
                "server_timestamp": last_sync.synced_at.isoformat(),
            })
        else:
            # No conflict: accept client change
            sync_log = SyncLog(
                user_id=user_id,
                device_id=device_id,
                entity_type=entity_type,
                entity_id=entity_id,
                action=SyncAction(action) if action in ("created", "updated", "deleted") else SyncAction.updated,
                payload_hash=payload_hash,
                conflict_detected=False,
            )
            db.add(sync_log)
            accepted += 1

    await db.commit()
    return {"accepted": accepted, "conflicts": conflicts}


async def pull_changes(
    db: AsyncSession,
    user_id: str,
    since: datetime,
) -> dict:
    """Pull changes since last sync timestamp."""
    result = await db.execute(
        select(SyncLog).where(
            SyncLog.user_id == user_id,
            SyncLog.synced_at > since,
        ).order_by(SyncLog.synced_at).limit(MAX_BATCH_SIZE)
    )
    logs = result.scalars().all()

    changes = [
        {
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "action": log.action.value,
            "server_timestamp": log.synced_at.isoformat(),
        }
        for log in logs
    ]

    return {
        "changes": changes,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


async def snapshot_progress(
    db: AsyncSession,
    user_id: str,
    snapshot_date: date | None = None,
) -> dict:
    """Aggregate daily progress snapshot."""
    from datetime import date as date_type
    if snapshot_date is None:
        snapshot_date = date_type.today()

    from src.models.learning import Lesson, LessonItem
    from src.models.sync import ProgressSnapshot

    # Get today's lessons
    result = await db.execute(
        select(Lesson).where(
            Lesson.user_id == user_id,
            Lesson.date == snapshot_date,
            Lesson.status == "completed",
        )
    )
    lessons = result.scalars().all()

    total_items = 0
    correct_items = 0
    study_seconds = 0
    accuracy_by_type: dict[str, list[bool]] = {}

    for lesson in lessons:
        items_result = await db.execute(
            select(LessonItem).where(LessonItem.lesson_id == lesson.id)
        )
        items = items_result.scalars().all()
        for item in items:
            if item.completed:
                total_items += 1
                if item.is_correct:
                    correct_items += 1
                study_seconds += item.time_spent_seconds or 0
                accuracy_by_type.setdefault(item.item_type.value, []).append(item.is_correct)

    # Calculate streak
    yesterday = snapshot_date.replace(day=snapshot_date.day - 1) if snapshot_date.day > 1 else snapshot_date
    prev = await db.execute(
        select(ProgressSnapshot).where(
            ProgressSnapshot.user_id == user_id,
            ProgressSnapshot.date == yesterday,
        )
    )
    prev_snapshot = prev.scalar_one_or_none()
    streak = (prev_snapshot.streak_days + 1) if prev_snapshot and prev_snapshot.lessons_completed > 0 else (1 if lessons else 0)

    snapshot = ProgressSnapshot(
        user_id=user_id,
        date=snapshot_date,
        words_learned=correct_items,
        study_minutes=study_seconds // 60,
        lessons_completed=len(lessons),
        streak_days=streak,
        accuracy_vocabulary=_accuracy_for_type(accuracy_by_type, "flashcard"),
        accuracy_reading=_accuracy_for_type(accuracy_by_type, "reading"),
        accuracy_grammar=_accuracy_for_type(accuracy_by_type, "grammar"),
        accuracy_listening=_accuracy_for_type(accuracy_by_type, "listening"),
    )
    db.add(snapshot)
    await db.commit()

    return {
        "streak": streak,
        "words_learned": correct_items,
        "study_minutes": study_seconds // 60,
        "lessons_completed": len(lessons),
    }


def _accuracy_for_type(data: dict[str, list[bool]], key: str) -> float | None:
    values = data.get(key, [])
    return sum(values) / len(values) if values else None
