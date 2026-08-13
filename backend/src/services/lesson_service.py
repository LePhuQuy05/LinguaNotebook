"""Lesson service — daily lesson generation and evaluation."""

from __future__ import annotations

import logging
import random
import re
from collections import Counter
from datetime import UTC, date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document_structure import DocumentStructure
from src.models.learning import ItemType, Lesson, LessonItem, LessonStatus
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

# Chapter-lesson retrieval: pull 2× the item budget from the chapter so
# trimming to `total_items` still leaves a book-ordered, non-repeating
# selection (and never fewer than MIN_RETRIEVAL_LIMIT).
CHAPTER_LIMIT_FACTOR = 2
MIN_RETRIEVAL_LIMIT = 10
LOG_TITLE_WIDTH = 30


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
            Schedule.is_active,
        )
    )
    schedules = schedule_result.scalars().all()
    today_schedules = [s for s in schedules if weekday in s.days_of_week]

    if not today_schedules:
        return None

    # Generate lesson from first matching schedule
    return await generate_lesson(db, user_id, today_schedules[0], lesson_date)


async def _next_chapter(db: AsyncSession, user_id: str) -> DocumentStructure | None:
    """The next chapter to study, across the user's mapped documents.

    Picks the most-advanced book (most completed chapters), then its
    lowest-order chapter without a completed lesson. Returns a
    DocumentStructure row, or None when no document has a map.
    """
    from src.models.document import Document
    from src.models.learning import Lesson as LessonModel

    result = await db.execute(
        select(DocumentStructure)
        .join(Document, Document.id == DocumentStructure.document_id)
        .where(Document.user_id == user_id)
        .order_by(DocumentStructure.order)
    )
    rows = result.scalars().all()
    if not rows:
        return None

    lessons = await db.execute(
        select(LessonModel.document_id, LessonModel.chapter_num).where(
            LessonModel.user_id == user_id,
            LessonModel.document_id.is_not(None),
            LessonModel.status == LessonStatus.completed,
        )
    )
    done = {(d, c) for d, c in lessons.all() if c is not None}

    per_doc = Counter(d for d, _ in done)
    rows_by_doc: dict[str, list[DocumentStructure]] = {}
    for row in rows:
        rows_by_doc.setdefault(row.document_id, []).append(row)

    # Books ordered by progress (most completed chapters first); the first
    # chapter without a completed lesson wins. If every chapter is done,
    # recycle the most-advanced book's last chapter.
    most_advanced = sorted(rows_by_doc, key=lambda d: -per_doc.get(d, 0))
    for doc_id in most_advanced:
        for row in rows_by_doc[doc_id]:
            if (row.document_id, row.chapter_num) not in done:
                return row
    return rows_by_doc[most_advanced[0]][-1]


def _chapter_query(chapter_title: str) -> str:
    """Japanese search query from a chapter title.

    Titles carry the English/Chinese gloss after the first Latin letter
    and often an explanation after a colon (人間関係1：家族と友達、性格).
    The Japanese topic is the prefix before the first of those; the query
    is "<topic>の言葉" (BGE-M3 matches Japanese queries best).
    """
    jp = re.split(r"[：:A-Za-z]", chapter_title)[0].strip(" ：:　")
    return f"{jp}の言葉" if jp else "言葉"


async def generate_lesson(
    db: AsyncSession,
    user_id: str,
    schedule: Schedule,
    lesson_date: date,
) -> Lesson:
    """Generate a daily lesson from RAG content + SRS reviews.

    Chapter-driven when the user has a document with a curriculum map
    (one chapter per lesson, vocab + exercises in book order); falls
    back to the generic content-type retrieval otherwise.
    """
    lesson = Lesson(
        user_id=user_id,
        schedule_id=schedule.id,
        date=lesson_date,
        status=LessonStatus.pending,
    )
    db.add(lesson)

    chapter = await _next_chapter(db, user_id)
    if chapter is not None:
        items = await _generate_chapter_lesson(
            db, user_id, schedule, lesson, chapter
        )
        if items:
            await db.commit()
            await db.refresh(lesson)
            return lesson
        # Empty retrieval (e.g. no chunks indexed yet) — fall through to
        # the generic path with the chapter attribution cleared.
        lesson.document_id = None
        lesson.chapter_num = None
        lesson.chapter_title = None

    await _generate_generic_lesson(db, user_id, schedule, lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


async def _generate_chapter_lesson(
    db: AsyncSession,
    user_id: str,
    schedule: Schedule,
    lesson: Lesson,
    chapter,
) -> list[LessonItem]:
    """Compose items from one curriculum chapter, in book order."""
    lesson.document_id = chapter.document_id
    lesson.chapter_num = chapter.chapter_num
    lesson.chapter_title = chapter.chapter_title

    total_items = schedule.daily_item_count
    search_results = await hybrid_search(
        user_id=user_id,
        query=_chapter_query(chapter.chapter_title),
        document_id=chapter.document_id,
        page_start=chapter.page_start,
        page_end=chapter.page_end,
        limit=max(total_items * CHAPTER_LIMIT_FACTOR, MIN_RETRIEVAL_LIMIT),
    )
    results = sorted(
        search_results.get("results", []),
        key=lambda r: (r.get("page_start", 0), r.get("chunk_index", 0)),
    )

    # Chunks stay in book order; the item type follows the schedule's
    # content types (round-robin) so a reading/grammar-heavy schedule
    # isn't silently overridden with vocabulary.
    item_types = schedule.content_types or ["vocabulary"]
    items: list[LessonItem] = []
    for order, sr in enumerate(results[:total_items]):
        content_type = item_types[order % len(item_types)]
        item = _create_lesson_item(lesson.id, content_type, sr, order)
        db.add(item)
        items.append(item)
    logger.info(
        f"Chapter lesson: {chapter.chapter_title[:LOG_TITLE_WIDTH]} (pages "
        f"{chapter.page_start}-{chapter.page_end}) → {len(items)} items"
    )
    return items


async def _generate_generic_lesson(
    db: AsyncSession,
    user_id: str,
    schedule: Schedule,
    lesson: Lesson,
) -> None:
    """The original content-type-driven composition (random retrieval)."""
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
    from datetime import datetime
    lesson.completed_at = datetime.now(UTC)
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


# Schedule content types map onto lesson item types. Vocabulary has no
# ItemType of its own — it is presented as a recall flashcard
# ("What does this term mean?").
_ITEM_TYPE_BY_CONTENT_TYPE: dict[str, ItemType] = {
    "vocabulary": ItemType.flashcard,
    "reading": ItemType.reading,
    "grammar": ItemType.grammar,
    "listening": ItemType.listening,
}


def _create_lesson_item(
    lesson_id: str,
    content_type: str,
    search_result: dict,
    order: int,
) -> LessonItem:
    """Create a lesson item from a RAG search result."""
    item_type = _ITEM_TYPE_BY_CONTENT_TYPE.get(content_type, ItemType.flashcard)
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
