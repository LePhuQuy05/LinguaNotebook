"""Lesson service — daily lesson generation and evaluation."""

import logging
import random
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.learning import Lesson, LessonItem, LessonStatus, ItemType
from src.models.schedule import Schedule
from src.services.rag_service import hybrid_search

logger = logging.getLogger(__name__)

# Default interleaving ratios
CONTENT_RATIOS = {
    "vocabulary": 0.40,
    "reading": 0.25,
    "grammar": 0.20,
    "listening": 0.15,
}


async def get_or_create_daily_lesson(
    db: AsyncSession,
    user_id: str,
    lesson_date: date | None = None,
) -> Lesson | None:
    """Get today's lesson, or generate one from active schedules."""
    if lesson_date is None:
        lesson_date = date.today()

    # Check for existing lesson
    result = await db.execute(
        select(Lesson).where(
            Lesson.user_id == user_id,
            Lesson.date == lesson_date,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Find active schedules for today
    weekday = lesson_date.isoweekday()
    schedule_result = await db.execute(
        select(Schedule).where(
            Schedule.user_id == user_id,
            Schedule.is_active == True,
        )
    )
    schedules = schedule_result.scalars().all()
    today_schedules = [s for s in schedules if weekday in s.days_of_week]

    if not today_schedules:
        return None

    # Generate lesson from first matching schedule
    return await generate_lesson(db, user_id, today_schedules[0], lesson_date)


async def generate_lesson(
    db: AsyncSession,
    user_id: str,
    schedule: Schedule,
    lesson_date: date,
) -> Lesson:
    """Generate a daily lesson from RAG content + SRS reviews."""
    lesson = Lesson(
        user_id=user_id,
        schedule_id=schedule.id,
        date=lesson_date,
        status=LessonStatus.pending,
    )
    db.add(lesson)

    total_items = schedule.daily_item_count
    items: list[LessonItem] = []

    # Calculate counts per content type
    type_counts: dict[str, int] = {}
    for ct in schedule.content_types:
        ratio = CONTENT_RATIOS.get(ct, 0.25)
        type_counts[ct] = max(1, int(total_items * ratio))

    # Fetch content from RAG for each type
    order = 0
    for content_type in schedule.content_types:
        count = type_counts.get(content_type, 3)

        # Search user's knowledge base
        search_results = await hybrid_search(
            user_id=user_id,
            query=_content_type_query(content_type),
            limit=count,
        )

        for sr in search_results.get("results", []):
            item = _create_lesson_item(lesson.id, content_type, sr, order)
            db.add(item)
            items.append(item)
            order += 1
            if order >= total_items:
                break
        if order >= total_items:
            break

    # Fill remaining with review cards from SRS
    if order < total_items:
        try:
            from src.services.srs_service import get_due_cards
            due = await get_due_cards(db, user_id, total_items - order)
            for card in due:
                item = LessonItem(
                    lesson_id=lesson.id,
                    item_type=ItemType.flashcard,
                    order_index=order,
                    question=card.front,
                    correct_answer=card.back,
                    knowledge_segment_id=card.knowledge_segment_id,
                )
                db.add(item)
                order += 1
        except Exception:
            pass  # SRS service not yet available

    # Interleave items (Fisher-Yates shuffle then reorder)
    random.shuffle(items)
    for i, item in enumerate(items):
        item.order_index = i

    await db.commit()
    await db.refresh(lesson)
    return lesson


async def answer_item(
    db: AsyncSession,
    lesson_id: str,
    item_id: str,
    user_id: str,
    response: str,
    time_spent_seconds: int = 0,
    self_rating: int | None = None,
) -> dict:
    """Evaluate a user's answer to a lesson item."""
    result = await db.execute(
        select(LessonItem).join(Lesson).where(
            LessonItem.id == item_id,
            Lesson.id == lesson_id,
            Lesson.user_id == user_id,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        return {"error": "Item not found"}

    item.user_response = response
    item.time_spent_seconds = time_spent_seconds

    # Evaluate correctness
    if item.item_type == ItemType.flashcard and self_rating is not None:
        item.self_rating = self_rating
        item.is_correct = self_rating >= 3  # SM-2 graduation threshold
    elif item.item_type == ItemType.listening:
        # Keyword presence for listening comprehension
        keywords = set(item.correct_answer.lower().split())
        response_words = set(response.lower().split())
        overlap = len(keywords & response_words)
        item.is_correct = overlap >= len(keywords) * 0.5
    else:
        # Case-insensitive, whitespace-normalized comparison
        normalized_response = " ".join(response.lower().split())
        normalized_answer = " ".join(item.correct_answer.lower().split())
        item.is_correct = normalized_response == normalized_answer

    item.completed = True
    await db.commit()

    return {
        "is_correct": item.is_correct,
        "correct_answer": item.correct_answer if not item.is_correct else None,
    }


async def complete_lesson(db: AsyncSession, lesson_id: str, user_id: str) -> dict:
    """Mark lesson as complete and calculate score."""
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id, Lesson.user_id == user_id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        return {"error": "Lesson not found"}

    # Calculate score
    items_result = await db.execute(
        select(LessonItem).where(LessonItem.lesson_id == lesson_id)
    )
    items = items_result.scalars().all()
    if items:
        completed = [i for i in items if i.completed]
        correct = [i for i in completed if i.is_correct]
        lesson.score = len(correct) / len(completed) if completed else 0
    else:
        lesson.score = 0

    lesson.status = LessonStatus.completed
    from datetime import datetime, timezone
    lesson.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "score": lesson.score,
        "words_learned": sum(1 for i in items if i.completed and i.is_correct),
        "streak_days": 1,  # Updated by progress service
    }


def _content_type_query(content_type: str) -> str:
    """Generate a search query optimized for each content type."""
    queries = {
        "vocabulary": "key terms and concepts",
        "reading": "comprehensive passage with main ideas",
        "grammar": "sentence structures and patterns",
        "listening": "descriptive passage suitable for listening",
    }
    return queries.get(content_type, "learning content")


def _create_lesson_item(
    lesson_id: str,
    content_type: str,
    search_result: dict,
    order: int,
) -> LessonItem:
    """Create a lesson item from a RAG search result."""
    item_type = ItemType(content_type)
    content = search_result.get("content", "")
    chunk_id = search_result.get("chunk_id")

    # Generate question based on content type
    if item_type == ItemType.flashcard:
        question = "What does this term mean?"
        answer = content
    elif item_type == ItemType.reading:
        question = "What is the main idea of this passage?"
        answer = content[:200] + "..."
    elif item_type == ItemType.grammar:
        question = "Complete the sentence using the correct form"
        answer = content
    elif item_type == ItemType.listening:
        question = "Listen to the passage and answer: what is the topic?"
        answer = content
    else:
        question = "Review this content"
        answer = content

    return LessonItem(
        lesson_id=lesson_id,
        knowledge_segment_id=chunk_id,
        item_type=item_type,
        order_index=order,
        question=question,
        correct_answer=answer,
    )
