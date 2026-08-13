"""Learning API endpoints — schedules, daily lessons, answers."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.services import lesson_service, rag_service, schedule_service

router = APIRouter(prefix="/api/v1", tags=["Learning"])


# ── Schedules ─────────────────────────────────────────────────

@router.get("/schedules")
async def list_schedules(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List user's study schedules."""
    schedules = await schedule_service.get_schedules(db, user_id)
    return [
        {
            "id": s.id,
            "name": s.name,
            "days_of_week": s.days_of_week,
            "time_of_day": s.time_of_day.isoformat(),
            "duration_minutes": s.duration_minutes,
            "content_types": s.content_types,
            "daily_item_count": s.daily_item_count,
            "is_active": s.is_active,
        }
        for s in schedules
    ]


@router.post("/schedules")
async def create_schedule(
    name: str = Query(...),
    days_of_week: str = Query("1,3,5"),
    time_of_day: str = Query("19:00"),
    duration_minutes: int = Query(30),
    content_types: str = Query("vocabulary,reading,grammar,listening"),
    daily_item_count: int = Query(10),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new study schedule."""
    days = [int(d) for d in days_of_week.split(",")]
    types = [t.strip() for t in content_types.split(",")]
    schedule = await schedule_service.create_schedule(
        db=db, user_id=user_id, name=name, days_of_week=days,
        time_of_day=time_of_day, duration_minutes=duration_minutes,
        content_types=types, daily_item_count=daily_item_count,
    )
    return {"id": schedule.id, "name": schedule.name}


@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    name: str | None = Query(None),
    is_active: bool | None = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a schedule."""
    s = await schedule_service.update_schedule(
        db, schedule_id, user_id, name=name, is_active=is_active,
    )
    if not s:
        raise HTTPException(404, "Schedule not found")
    return {"id": s.id}


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a schedule."""
    deleted = await schedule_service.delete_schedule(db, schedule_id, user_id)
    if not deleted:
        raise HTTPException(404, "Schedule not found")
    return {"status": "deleted"}


# ── Lessons ───────────────────────────────────────────────────

@router.get("/lessons/daily")
async def daily_lesson(
    lesson_date: date | None = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get or generate today's lesson."""
    lesson = await lesson_service.get_or_create_daily_lesson(db, user_id, lesson_date)
    if not lesson:
        return {"lesson": None, "message": "No active schedule for today"}

    # Load items
    from sqlalchemy import select

    from src.models.learning import LessonItem
    items_result = await db.execute(
        select(LessonItem).where(LessonItem.lesson_id == lesson.id).order_by(LessonItem.order_index)
    )
    items = items_result.scalars().all()

    # Source book filename for the chapter-attribution banner
    document_filename = None
    if lesson.document_id:
        from src.models.document import Document
        src_doc = (
            await db.execute(select(Document).where(Document.id == lesson.document_id))
        ).scalar_one_or_none()
        document_filename = src_doc.filename if src_doc else None

    # Batch-fetch each item's source chunk from Qdrant (point id → payload)
    source_ids = [i.knowledge_segment_id for i in items if i.knowledge_segment_id]
    item_sources = rag_service.get_chunk_sources(user_id, source_ids)

    return {
        "lesson": {
            "id": lesson.id,
            "date": lesson.date.isoformat(),
            "status": lesson.status.value,
            "score": lesson.score,
            "document_id": lesson.document_id,
            "document_filename": document_filename,
            "chapter_num": lesson.chapter_num,
            "chapter_title": lesson.chapter_title,
        },
        "items": [
            {
                "id": i.id,
                "item_type": i.item_type.value,
                "order_index": i.order_index,
                "question": i.question,
                "correct_answer": i.correct_answer,
                "completed": i.completed,
                "is_correct": i.is_correct,
                "source": item_sources.get(i.knowledge_segment_id),
            }
            for i in items
        ],
    }


@router.post("/lessons/{lesson_id}/items/{item_id}/answer")
async def answer_item(
    lesson_id: str,
    item_id: str,
    response: str = Query(...),
    time_spent_seconds: int = Query(0),
    self_rating: int | None = Query(None, ge=1, le=5),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit an answer for a lesson item."""
    result = await lesson_service.answer_item(
        db, lesson_id, item_id, user_id, response, time_spent_seconds, self_rating,
    )
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Complete a lesson and calculate score."""
    result = await lesson_service.complete_lesson(db, lesson_id, user_id)
    if "error" in result:
        raise HTTPException(404, result["error"])
    return result
