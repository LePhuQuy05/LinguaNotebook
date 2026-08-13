"""E2E verification for 007 tickets 02 + 05 (run after the embed lands).

1. Qdrant has points for the user's collection and hybrid_search returns
   results with real page numbers (ticket 02).
2. get_or_create_daily_lesson produces a chapter-driven lesson: attribution
   set to the mapped document + chapter, and every item's source chunk falls
   inside that chapter's page range (ticket 05, AC6).
"""

import asyncio
import sys
from datetime import date, time

from sqlalchemy import select

from src.core.database import AsyncSessionLocal
# Register all models in the app's lifespan order so SQLAlchemy's mapper
# configuration can resolve every foreign key (schedules.user_id → users.id,
# lesson_items.knowledge_segment_id → knowledge_segments.id, ...).
from src.models.user import User  # noqa: F401
from src.models.document import Document, ContentBlock  # noqa: F401
from src.models.knowledge_segment import KnowledgeSegment  # noqa: F401
from src.models.schedule import Schedule
from src.models.learning import Lesson, LessonItem
from src.models.srs import SRSCard  # noqa: F401
from src.models.sync import Device, SyncLog, ProgressSnapshot  # noqa: F401
from src.models.document_structure import DocumentStructure
from src.services.lesson_service import get_or_create_daily_lesson
from src.services.rag_service import hybrid_search

USER = "5f215c76-9fb5-4d48-901c-1f55132d7656"
DOC = "16116abe-8d2d-4855-90a5-01cd88b818fb"
LESSON_DATE = date(2026, 8, 14)  # Thursday, isoweekday 4


def _coll_count():
    from src.core.qdrant import get_collection_name, qdrant_client
    return qdrant_client.get_collection(get_collection_name(USER)).points_count


async def main() -> int:
    fails = []

    # --- Ticket 02: Qdrant live + hybrid search returns page-accurate results
    count = _coll_count()
    print(f"[02] collection points: {count}")
    if count <= 0:
        fails.append("ticket 02: Qdrant collection has 0 points")

    res = await hybrid_search(user_id=USER, query="天気の言葉", document_id=DOC, limit=5)
    results = res.get("results", [])
    print(f"[02] hybrid_search('天気の言葉', doc) → {len(results)} results, took {res.get('took_ms')}ms")
    for r in results[:5]:
        print(f"      page {r['page_start']} idx {r['chunk_index']} | {r['content'][:40]!r}")
    if not results:
        fails.append("ticket 02: hybrid_search returned nothing")
    elif all(r["page_start"] == 1 for r in results):
        fails.append("ticket 02: page_start still hardcoded to 1 (page metadata missing)")

    # --- Ticket 05: chapter-driven daily lesson
    async with AsyncSessionLocal() as db:
        structures = (
            (await db.execute(
                select(DocumentStructure).where(DocumentStructure.document_id == DOC)
            ))
            .scalars().all()
        )
        print(f"[05] curriculum rows for doc: {len(structures)}")
        if not structures:
            fails.append("ticket 05: no curriculum map for the document")

        # Ensure a schedule covers today
        sched = (
            (await db.execute(
                select(Schedule).where(Schedule.user_id == USER, Schedule.is_active)
            ))
            .scalars().first()
        )
        if sched is None or LESSON_DATE.isoweekday() not in sched.days_of_week:
            print("[05] creating a daily schedule (vocabulary x5, Mon-Sun)")
            sched = Schedule(
                user_id=USER,
                name="e2e-daily",
                days_of_week=[1, 2, 3, 4, 5, 6, 7],
                time_of_day=time(9, 0),
                duration_minutes=10,
                content_types=["vocabulary"],
                daily_item_count=5,
            )
            db.add(sched)
            await db.commit()
            await db.refresh(sched)

        lesson = await get_or_create_daily_lesson(db, USER, LESSON_DATE)
        if lesson is None:
            fails.append("ticket 05: get_or_create_daily_lesson returned None")
            await db.rollback()
            return 1

        print(f"[05] lesson {lesson.id[:8]} → doc {lesson.document_id} "
              f"chapter {lesson.chapter_num} title {lesson.chapter_title!r}")
        if lesson.document_id != DOC or lesson.chapter_num is None:
            fails.append("ticket 05: lesson not attributed to a curriculum chapter")

        # Pull the lesson's chapter page range
        chap = next((s for s in structures if s.chapter_num == lesson.chapter_num), None)
        items = (
            (await db.execute(
                select(LessonItem).where(LessonItem.lesson_id == lesson.id)
            ))
            .scalars().all()
        )
        print(f"[05] {len(items)} items")
        if chap is not None:
            lo, hi = chap.page_start, chap.page_end or 10**6
            print(f"[05] chapter pages {lo}-{hi}; item chunk pages: "
                  f"{[i.knowledge_segment_id[:8] for i in items]}")
            # Verify each item's source chunk falls inside the chapter range
            from src.core.qdrant import get_collection_name, qdrant_client
            ids = [i.knowledge_segment_id for i in items if i.knowledge_segment_id]
            if ids:
                points = qdrant_client.retrieve(
                    collection_name=get_collection_name(USER), ids=ids, with_payload=True
                )
                pages = [p.payload.get("page_start") for p in points]
                print(f"[05] chunk page_starts: {pages}")
                if not all(lo <= (p or 0) <= hi for p in pages):
                    fails.append(
                        "ticket 05: some item chunks fall outside the chapter page range"
                    )
        else:
            fails.append("ticket 05: lesson chapter not found in curriculum map")

    if fails:
        print("\nFAILURES:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nALL E2E CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
