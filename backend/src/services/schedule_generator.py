"""Study Schedule Generator — creates personalized learning plans from OCR content.

Generates daily schedules using SM-2 spaced repetition,
adapts to user pace, and outputs in frontend-compatible format.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from src.services.structure_extractor import DocumentStructure, Chapter, classify_topic

logger = logging.getLogger(__name__)


class LessonType(str, Enum):
    VOCABULARY = "vocabulary"
    READING = "reading"
    GRAMMAR = "grammar"
    REVIEW = "review"
    QUIZ = "quiz"


class Difficulty(str, Enum):
    BEGINNER = "N5"
    ELEMENTARY = "N4"
    INTERMEDIATE = "N3"
    UPPER_INTERMEDIATE = "N2"
    ADVANCED = "N1"


@dataclass
class DailyLesson:
    """A single day's study plan."""
    day: int
    date: date
    chapter: str = ""
    chapter_number: int = 0
    topic: str = ""
    lesson_type: LessonType = LessonType.VOCABULARY
    estimated_minutes: int = 30
    items_to_review: list[str] = field(default_factory=list)  # SM-2 items due
    new_items: int = 10  # new vocab/flashcards to learn
    completed: bool = False


@dataclass
class StudyPlan:
    """Full study plan for a document."""
    document_id: str = ""
    document_title: str = ""
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    total_days: int = 0
    start_date: date = field(default_factory=lambda: date.today())
    end_date: date = field(default_factory=lambda: date.today())
    chapters_per_day: int = 1
    lessons: list[DailyLesson] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Study time estimates by JLPT level and lesson type (minutes)
STUDY_TIME_ESTIMATES = {
    Difficulty.INTERMEDIATE: {
        LessonType.VOCABULARY: 25,
        LessonType.READING: 20,
        LessonType.GRAMMAR: 20,
        LessonType.REVIEW: 15,
        LessonType.QUIZ: 10,
    },
    Difficulty.UPPER_INTERMEDIATE: {
        LessonType.VOCABULARY: 30,
        LessonType.READING: 25,
        LessonType.GRAMMAR: 25,
        LessonType.REVIEW: 15,
        LessonType.QUIZ: 10,
    },
}

# Items per session by level
NEW_ITEMS_PER_SESSION = {
    Difficulty.BEGINNER: 15,
    Difficulty.ELEMENTARY: 12,
    Difficulty.INTERMEDIATE: 10,
    Difficulty.UPPER_INTERMEDIATE: 8,
    Difficulty.ADVANCED: 5,
}

# SM-2 review intervals (days)
SM2_INTERVALS = [1, 3, 7, 14, 30, 60, 120, 240]


def generate_study_plan(
    structure: DocumentStructure,
    document_id: str = "",
    start_date: date | None = None,
    chapters_per_day: int = 1,
    difficulty: Difficulty = Difficulty.INTERMEDIATE,
    lessons_per_week: int = 7,
) -> StudyPlan:
    """Generate a complete study plan from document structure.

    Args:
        structure: Parsed document structure from StructureExtractor
        document_id: The document this plan is for
        start_date: When to start (default: next Monday)
        chapters_per_day: How many chapters to cover per study day
        difficulty: JLPT level (affects pacing)
        lessons_per_week: Study days per week (default: every day)
    """
    if start_date is None:
        # Start next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        start_date = today + timedelta(days=days_until_monday or 7)

    plan = StudyPlan(
        document_id=document_id,
        document_title=structure.title,
        difficulty=difficulty,
        start_date=start_date,
        chapters_per_day=chapters_per_day,
    )

    time_estimates = STUDY_TIME_ESTIMATES.get(difficulty, STUDY_TIME_ESTIMATES[Difficulty.INTERMEDIATE])
    new_items = NEW_ITEMS_PER_SESSION.get(difficulty, 10)

    chapters = structure.chapters
    if not chapters:
        logger.warning("No chapters found in structure — generating empty plan")
        return plan

    # Group chapters by topic for interleaved learning
    topic_chapters: dict[str, list[Chapter]] = {}
    for ch in chapters:
        topic_chapters.setdefault(ch.topic, []).append(ch)

    # Generate lessons: alternate between new content and review days
    lesson_list: list[DailyLesson] = []
    study_day = 0
    chapter_index = 0
    current_date = start_date

    # Create a flattened chapter list interleaved by topic
    # (don't do all "human_relations" chapters back-to-back)
    chapter_queue = _interleave_chapters(topic_chapters)

    while chapter_index < len(chapter_queue):
        study_day += 1

        # Skip rest days
        day_of_week = current_date.weekday()
        if day_of_week >= lessons_per_week:
            current_date += timedelta(days=1)
            continue

        # Every 5th day is a review/quiz day
        if study_day % 5 == 0:
            lesson_list.append(DailyLesson(
                day=study_day,
                date=current_date,
                lesson_type=LessonType.REVIEW,
                estimated_minutes=time_estimates[LessonType.REVIEW],
                items_to_review=[f"Review items from days {study_day - 4}–{study_day - 1}"],
                new_items=0,
            ))
            current_date += timedelta(days=1)
            continue

        # Every 10th day is a quiz day
        if study_day % 10 == 0:
            lesson_list.append(DailyLesson(
                day=study_day,
                date=current_date,
                lesson_type=LessonType.QUIZ,
                estimated_minutes=time_estimates[LessonType.QUIZ],
                items_to_review=[f"Quiz covering all material up to day {study_day - 1}"],
                new_items=0,
            ))
            current_date += timedelta(days=1)
            continue

        # Regular study day — cover chapter(s)
        for _ in range(chapters_per_day):
            if chapter_index >= len(chapter_queue):
                break

            ch = chapter_queue[chapter_index]
            chapter_index += 1

            # Determine topics to review today (SM-2 based)
            review_items = _get_sm2_review_items(lesson_list, study_day)

            lesson_list.append(DailyLesson(
                day=study_day,
                date=current_date,
                chapter=ch.title_jp,
                chapter_number=ch.number,
                topic=ch.topic,
                lesson_type=LessonType.VOCABULARY,
                estimated_minutes=time_estimates[LessonType.VOCABULARY],
                items_to_review=review_items,
                new_items=new_items,
            ))

        current_date += timedelta(days=1)

    plan.lessons = lesson_list
    plan.total_days = study_day
    plan.end_date = current_date - timedelta(days=1)

    logger.info(
        f"Generated study plan: {plan.total_days} days, "
        f"{len(chapters)} chapters, {plan.start_date} → {plan.end_date}"
    )
    return plan


def _interleave_chapters(topic_chapters: dict[str, list[Chapter]]) -> list[Chapter]:
    """Interleave chapters from different topics for variety."""
    result = []
    topic_lists = list(topic_chapters.values())
    max_len = max(len(lst) for lst in topic_lists)

    for i in range(max_len):
        for lst in topic_lists:
            if i < len(lst):
                result.append(lst[i])

    return result


def _get_sm2_review_items(lessons: list[DailyLesson], current_day: int) -> list[str]:
    """Determine which items should be reviewed today based on SM-2 intervals."""
    review_items = []

    for interval_days in SM2_INTERVALS:
        review_day = current_day - interval_days
        if review_day <= 0:
            continue

        for lesson in lessons:
            if lesson.day == review_day and lesson.chapter:
                review_items.append(
                    f"Day {review_day}: {lesson.chapter} (interval: {interval_days}d)"
                )
                break

    return review_items[-5:]  # Limit to 5 review items per day


def format_plan_for_frontend(plan: StudyPlan) -> dict:
    """Convert study plan to frontend-compatible dict."""
    return {
        "document_id": plan.document_id,
        "document_title": plan.document_title,
        "difficulty": plan.difficulty.value,
        "total_days": plan.total_days,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "chapters_per_day": plan.chapters_per_day,
        "progress": {
            "completed_lessons": sum(1 for l in plan.lessons if l.completed),
            "total_lessons": len(plan.lessons),
            "completion_pct": round(
                sum(1 for l in plan.lessons if l.completed) / max(len(plan.lessons), 1) * 100
            ),
        },
        "lessons": [
            {
                "day": l.day,
                "date": l.date.isoformat(),
                "chapter": l.chapter,
                "chapter_number": l.chapter_number,
                "topic": l.topic,
                "type": l.lesson_type.value,
                "estimated_minutes": l.estimated_minutes,
                "items_to_review": l.items_to_review,
                "new_items": l.new_items,
                "completed": l.completed,
            }
            for l in plan.lessons
        ],
    }


def estimate_completion(plan: StudyPlan) -> str:
    """Human-readable completion estimate."""
    weeks = plan.total_days / 7
    if weeks <= 1:
        return f"{plan.total_days} days"
    elif weeks <= 4:
        return f"~{weeks:.0f} weeks"
    else:
        months = weeks / 4.3
        return f"~{months:.0f} months"
