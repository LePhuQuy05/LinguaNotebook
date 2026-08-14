"""Lesson generation tests — chapter-driven composition (007-05).

Lessons with a curriculum map must come from one chapter (vocab +
exercises in book order), track document/chapter, and fall back to the
generic content-type retrieval when there is no map or no chunks yet.
"""

import asyncio
import types
from datetime import date

import pytest

from src.models.learning import ItemType, Lesson, LessonItem, LessonStatus
from src.services import lesson_service
from src.services.item_generators import GeneratedItem
from src.services.lesson_service import _chapter_query, _next_chapter


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        value = self._value
        if isinstance(value, list):
            return value[0] if len(value) == 1 else None
        return value

    def scalars(self):
        return _FakeScalars(self._value)

    def all(self):
        return self._value


class _FakeScalars:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else [items]

    def all(self):
        return self._items


class FakeDB:
    def __init__(self, structures=None, completed=None, schedules=None):
        self.structures = structures or []
        self.completed = completed or []
        self.schedules = schedules or []
        self.added = []

    @staticmethod
    def _table_name(obj):
        name = getattr(obj, "name", None)
        if not name:
            name = getattr(obj, "__tablename__", None)
        return name or ""

    async def execute(self, statement):
        # `_next_chapter` selects DocumentStructure JOIN Document, so
        # the first FROM is a Join (no .name) — walk left to the base table.
        first = statement.get_final_froms()[0] if statement.get_final_froms() else None
        name = self._table_name(first)
        while not name and first is not None and hasattr(first, "left"):
            first = first.left
            name = self._table_name(first)
        if name == "document_structures":
            return FakeResult(self.structures)
        if name == "lessons":
            return FakeResult(self.completed)
        if name == "schedules":
            return FakeResult(self.schedules)
        return FakeResult([])

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def _chapter(doc, num, title, start, end, order):
    return types.SimpleNamespace(
        document_id=doc,
        chapter_num=num,
        chapter_title=title,
        page_start=start,
        page_end=end,
        order=order,
    )


def _schedule(content_types=("vocabulary",), daily_item_count=4, days_of_week=(5,)):
    return types.SimpleNamespace(
        id="s1",
        content_types=list(content_types),
        daily_item_count=daily_item_count,
        days_of_week=list(days_of_week),
    )


class TestNextChapter:
    @pytest.mark.asyncio
    async def test_returns_first_uncompleted_chapter(self):
        db = FakeDB(
            structures=[_chapter("d1", 1, "人・体", 2, 5, 0), _chapter("d1", 2, "天気", 6, 9, 1)],
            completed=[("d1", 1)],
        )

        chapter = await _next_chapter(db, "user-1")

        assert chapter.chapter_num == 2

    @pytest.mark.asyncio
    async def test_returns_none_without_map(self):
        assert await _next_chapter(FakeDB(), "user-1") is None

    @pytest.mark.asyncio
    async def test_recycles_last_chapter_when_all_completed(self):
        db = FakeDB(
            structures=[_chapter("d1", 1, "人・体", 2, 5, 0)],
            completed=[("d1", 1)],
        )

        chapter = await _next_chapter(db, "user-1")

        assert chapter.chapter_num == 1

    @pytest.mark.asyncio
    async def test_picks_most_advanced_book_first(self):
        # d2 has 2 completed chapters, d1 has 1 → the next chapter must
        # come from d2, even though d1 is earlier in the map.
        db = FakeDB(
            structures=[
                _chapter("d1", 1, "人・体", 2, 5, 0),
                _chapter("d2", 1, "学校", 2, 5, 1),
                _chapter("d2", 2, "天気", 6, 9, 2),
                _chapter("d2", 3, "趣味", 10, 13, 3),
            ],
            completed=[("d1", 1), ("d2", 1), ("d2", 2)],
        )

        chapter = await _next_chapter(db, "user-1")

        assert chapter.document_id == "d2"
        assert chapter.chapter_num == 3


class TestChapterQuery:
    def test_extracts_japanese_prefix(self):
        assert _chapter_query("人間関係1：家族と友達、性格 Human relations 1") == "人間関係1の言葉"

    def test_pure_japanese_title(self):
        assert _chapter_query("語形成 Word-compounding 复合词") == "語形成の言葉"

    def test_empty_title_falls_back(self):
        assert _chapter_query("") == "言葉"


class TestGenerateLesson:
    @pytest.fixture
    def setup(self, monkeypatch):
        state = {"calls": [], "empty_chapter": False}

        async def fake_search(user_id, query, **kwargs):
            state["calls"].append({"query": query, **kwargs})
            if state["empty_chapter"] and kwargs.get("document_id"):
                return {"results": []}
            # Source pages all inside the chapter used by the fake
            # (天気 spans pages 6-9): (6,0), (7,1), (9,2).
            return {
                "results": [
                    {
                        "chunk_id": f"c{i}",
                        "content": f"内容{i}",
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": page,
                        "chunk_index": idx,
                        "score": 1.0,
                    }
                    for i, (page, idx) in enumerate([(6, 0), (7, 1), (9, 2)])
                ]
            }

        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)
        return state

    @staticmethod
    def _fake_next_chapter():
        async def fake_next(db, uid):
            return _chapter("d1", 2, "天気", 6, 9, 1)

        return fake_next

    @pytest.mark.asyncio
    async def test_chapter_path_sets_lesson_attribution_and_sorts_by_page(self, monkeypatch, setup):
        monkeypatch.setattr(lesson_service, "_next_chapter", self._fake_next_chapter())
        db = FakeDB()

        lesson = await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=3), types.SimpleNamespace()
        )

        assert lesson.document_id == "d1"
        assert lesson.chapter_num == 2
        # items in book order: pages 6, 7, 9 → contents 内容0, 内容1, 内容2
        items = [a for a in db.added if type(a).__name__ == "LessonItem"]
        assert [i.correct_answer for i in items] == ["内容0", "内容1", "内容2"]
        # retrieval scoped to the chapter (document + page range), so every
        # item's source page falls inside the chapter's 6-9 range
        chapter_call = setup["calls"][0]
        assert chapter_call["document_id"] == "d1"
        assert chapter_call["page_start"] == 6
        assert chapter_call["page_end"] == 9

    @pytest.mark.asyncio
    async def test_chapter_path_respects_schedule_content_types(self, monkeypatch, setup):
        monkeypatch.setattr(lesson_service, "_next_chapter", self._fake_next_chapter())
        db = FakeDB()

        await lesson_service.generate_lesson(
            db,
            "u",
            _schedule(content_types=["vocabulary", "grammar"], daily_item_count=3),
            types.SimpleNamespace(),
        )

        # Item types follow the schedule, round-robin over the chapter's
        # chunks in book order (vocabulary → flashcard).
        items = [a for a in db.added if type(a).__name__ == "LessonItem"]
        assert [i.item_type for i in items] == [
            ItemType.flashcard,
            ItemType.grammar,
            ItemType.flashcard,
        ]

    @pytest.mark.asyncio
    async def test_falls_back_to_generic_when_retrieval_empty(self, monkeypatch, setup):
        monkeypatch.setattr(lesson_service, "_next_chapter", self._fake_next_chapter())
        setup["empty_chapter"] = True
        db = FakeDB()

        lesson = await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=3), types.SimpleNamespace()
        )

        # chapter attribution cleared; generic queries used
        assert lesson.document_id is None
        assert lesson.chapter_num is None
        generic = [c for c in setup["calls"] if not c.get("document_id")]
        assert generic, "generic retrieval must run after empty chapter retrieval"
        assert generic[0]["query"] == "key terms and concepts"

    @pytest.mark.asyncio
    async def test_generic_path_without_map(self, monkeypatch, setup):
        async def fake_none(db, uid):
            return None

        monkeypatch.setattr(lesson_service, "_next_chapter", fake_none)
        db = FakeDB()

        lesson = await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=3), types.SimpleNamespace()
        )

        assert lesson.document_id is None
        generic = [c for c in setup["calls"] if not c.get("document_id")]
        assert generic, "generic retrieval must run when there is no map"

    @pytest.mark.asyncio
    async def test_items_carry_structured_data_from_generator(self, monkeypatch, setup):
        monkeypatch.setattr(lesson_service, "_next_chapter", self._fake_next_chapter())
        db = FakeDB()

        await lesson_service.generate_lesson(
            db,
            "u",
            _schedule(content_types=["reading"], daily_item_count=2),
            types.SimpleNamespace(),
        )

        items = [a for a in db.added if type(a).__name__ == "LessonItem"]
        assert len(items) == 2
        for item in items:
            assert item.data is not None
            assert len(item.data["options"]) == 4
            assert item.data["options"][item.data["correct_index"]] == item.correct_answer

    @pytest.mark.asyncio
    async def test_chapter_path_backfills_skipped_chunks(self, monkeypatch):
        async def fake_search(user_id, query, **kwargs):
            # 6 results; every other chunk is empty (skipped by the generator).
            return {
                "results": [
                    {
                        "chunk_id": f"c{i}",
                        "content": ("" if i % 2 else f"内容{i}"),
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": 6 + i,
                        "chunk_index": i,
                        "score": 1.0,
                    }
                    for i in range(6)
                ]
            }

        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)
        monkeypatch.setattr(lesson_service, "_next_chapter", self._fake_next_chapter())
        db = FakeDB()

        await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=3), types.SimpleNamespace()
        )

        # The 2× retrieval buffer absorbs the skipped chunks, so the lesson
        # still fills to the daily item count instead of silently under-filling.
        items = [a for a in db.added if type(a).__name__ == "LessonItem"]
        assert len(items) == 3
        assert [i.correct_answer for i in items] == ["内容0", "内容2", "内容4"]

    def test_create_lesson_item_skips_empty_chunk(self):
        # The generator skips empty content; the lesson item is not created.
        item = asyncio.run(
            lesson_service._create_lesson_item(
                "l1", "vocabulary", {"chunk_id": "c0", "content": ""}, 0
            )
        )
        assert item is None

    def test_create_lesson_item_defaults_unknown_content_type_to_flashcard(self):
        # Unknown content types degrade to the flashcard safe default, so
        # ItemType(item.item_type) never raises ValueError.
        item = asyncio.run(
            lesson_service._create_lesson_item(
                "l1", "mystery", {"chunk_id": "c0", "content": "内容0"}, 0
            )
        )
        assert item is not None
        assert item.item_type == ItemType.flashcard
        assert item.data["term"] == "内容0"


class _RecordingGenerator:
    """A generator seam double that records every call's context."""

    def __init__(self):
        self.calls = []

    async def generate(self, chunk, content_type, context=None):
        self.calls.append((chunk, content_type, context))
        return [
            GeneratedItem(
                item_type="flashcard",
                question="q",
                correct_answer="a",
                payload={
                    "term": chunk.get("content", ""),
                    "reading": "",
                    "definition": "a",
                    "example": "",
                },
            )
        ]


class TestChapterContext:
    """Feature 009 (ticket 05): chapter lessons build the whole-chapter
    context and thread it into the generator seam for the SLM to read."""

    @pytest.fixture
    def setup(self, monkeypatch):
        async def fake_search(user_id, query, **kwargs):
            return {
                "results": [
                    {
                        "chunk_id": f"c{i}",
                        "content": f"内容{i}",
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": 6 + i,
                        "chunk_index": i,
                        "score": 1.0,
                    }
                    for i in range(3)
                ]
            }

        async def fake_next(db, uid):
            return _chapter("d1", 2, "天気", 6, 9, 1)

        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)
        monkeypatch.setattr(lesson_service, "_next_chapter", fake_next)

    @pytest.mark.asyncio
    async def test_chapter_context_threaded_and_cache_shared(self, monkeypatch, setup):
        recording = _RecordingGenerator()
        monkeypatch.setattr(lesson_service, "get_item_generator", lambda: recording)
        db = FakeDB()

        await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=2), types.SimpleNamespace()
        )

        assert len(recording.calls) == 2
        caches = []
        for chunk, _ct, context in recording.calls:
            assert context is not None
            assert context["chapter_title"] == "天気"
            assert [c["chunk_id"] for c in context["chunks"]] == ["c0", "c1"]
            assert context["plan"] == ["vocabulary", "vocabulary"]
            caches.append(id(context["_cache"]))
        # one shared cache for the whole lesson → the SLM plans one model pass
        assert len(set(caches)) == 1

    @pytest.mark.asyncio
    async def test_generic_lesson_passes_no_context(self, monkeypatch):
        async def fake_none(db, uid):
            return None

        async def fake_search(user_id, query, **kwargs):
            return {
                "results": [
                    {
                        "chunk_id": "c0",
                        "content": "内容0",
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": 1,
                        "chunk_index": 0,
                        "score": 1.0,
                    }
                ]
            }

        monkeypatch.setattr(lesson_service, "_next_chapter", fake_none)
        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)
        recording = _RecordingGenerator()
        monkeypatch.setattr(lesson_service, "get_item_generator", lambda: recording)
        db = FakeDB()

        await lesson_service.generate_lesson(
            db, "u", _schedule(daily_item_count=1), types.SimpleNamespace()
        )

        assert recording.calls[0][2] is None


class TestExplicitChapter:
    @pytest.mark.asyncio
    async def test_explicit_chapter_skips_next_chapter(self, monkeypatch):
        async def boom(db, uid):
            raise AssertionError("_next_chapter must not run for an explicit chapter")

        async def fake_search(user_id, query, **kwargs):
            return {
                "results": [
                    {
                        "chunk_id": "c0",
                        "content": "内容0",
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": 6,
                        "chunk_index": 0,
                        "score": 1.0,
                    }
                ]
            }

        monkeypatch.setattr(lesson_service, "_next_chapter", boom)
        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)
        db = FakeDB()

        lesson = await lesson_service.generate_lesson(
            db,
            "u",
            _schedule(daily_item_count=1),
            types.SimpleNamespace(),
            chapter=_chapter("d1", 2, "天気", 6, 9, 1),
        )

        assert lesson.document_id == "d1"
        assert lesson.chapter_num == 2


class TestGetOrCreateWithChapter:
    """Book picker flow: `chapter_id` on the daily lesson endpoint."""

    @pytest.fixture
    def setup(self, monkeypatch):
        async def fake_search(user_id, query, **kwargs):
            return {
                "results": [
                    {
                        "chunk_id": "c0",
                        "content": "内容0",
                        "document_id": "d1",
                        "block_type": "paragraph",
                        "language": "ja",
                        "difficulty": "intermediate",
                        "page_start": 6,
                        "chunk_index": 0,
                        "score": 1.0,
                    }
                ]
            }

        monkeypatch.setattr(lesson_service, "hybrid_search", fake_search)

    @pytest.mark.asyncio
    async def test_chapter_id_generates_fresh_lesson_from_that_chapter(self, monkeypatch, setup):
        db = FakeDB(
            structures=[_chapter("d1", 2, "天気", 6, 9, 1)],
            schedules=[_schedule(daily_item_count=2)],
        )

        lesson = await lesson_service.get_or_create_daily_lesson(
            db, "u", date(2026, 8, 14), chapter_id="ch1"
        )

        assert lesson is not None
        assert lesson.document_id == "d1"
        assert lesson.chapter_num == 2

    @pytest.mark.asyncio
    async def test_chapter_id_reuses_todays_existing_chapter_lesson(self, monkeypatch, setup):
        existing = Lesson(
            id="l1",
            user_id="u",
            schedule_id="s1",
            date=date(2026, 8, 14),
            status=LessonStatus.pending,
            document_id="d1",
            chapter_num=2,
        )
        db = FakeDB(
            structures=[_chapter("d1", 2, "天気", 6, 9, 1)],
            completed=[existing],
            schedules=[_schedule(daily_item_count=2)],
        )

        lesson = await lesson_service.get_or_create_daily_lesson(
            db, "u", date(2026, 8, 14), chapter_id="ch1"
        )

        assert lesson is existing

    @pytest.mark.asyncio
    async def test_chapter_id_not_owned_returns_none(self, monkeypatch, setup):
        db = FakeDB(structures=[], schedules=[_schedule(daily_item_count=2)])

        lesson = await lesson_service.get_or_create_daily_lesson(
            db, "u", date(2026, 8, 14), chapter_id="ch1"
        )

        assert lesson is None


class TestCompleteLesson:
    @pytest.mark.asyncio
    async def test_scores_answered_items(self):
        lesson = Lesson(
            id="l1",
            user_id="u",
            schedule_id="s1",
            date=date(2026, 1, 1),
            status=LessonStatus.pending,
        )
        items = [
            LessonItem(
                id="i1",
                lesson_id="l1",
                item_type=ItemType.flashcard,
                order_index=0,
                question="q",
                correct_answer="a",
                completed=True,
                is_correct=True,
            ),
            LessonItem(
                id="i2",
                lesson_id="l1",
                item_type=ItemType.flashcard,
                order_index=1,
                question="q",
                correct_answer="a",
                completed=True,
                is_correct=False,
            ),
            LessonItem(
                id="i3",
                lesson_id="l1",
                item_type=ItemType.reading,
                order_index=2,
                question="q",
                correct_answer="a",
                completed=False,
                is_correct=None,
            ),
        ]

        class _DB(FakeDB):
            def __init__(self):
                super().__init__()
                self.lesson = lesson
                self.items = items

            async def execute(self, statement) -> FakeResult:
                first = statement.get_final_froms()[0]
                name = getattr(first, "name", None)
                return FakeResult(self.lesson if name == "lessons" else self.items)

        result = await lesson_service.complete_lesson(_DB(), "l1", "u")

        assert lesson.score == 0.5
        assert lesson.status == LessonStatus.completed
        assert lesson.completed_at is not None
        assert result["score"] == 0.5
        assert result["words_learned"] == 1


class TestAnswerItem:
    class _FakeDB(FakeDB):
        def __init__(self, item):
            super().__init__()
            self.item = item

        async def execute(self, statement) -> FakeResult:
            return FakeResult(self.item)

    @staticmethod
    def _fake_db(item):
        return TestAnswerItem._FakeDB(item)

    @staticmethod
    def _item(item_type, data=None, correct_answer="answer"):
        return LessonItem(
            lesson_id="l1",
            item_type=item_type,
            correct_answer=correct_answer,
            data=data,
            question="q",
            order_index=0,
        )

    @pytest.mark.asyncio
    async def test_mc_item_graded_by_exact_option_index(self):
        item = self._item(
            ItemType.grammar,
            data={"options": ["a", "b", "c", "d"], "correct_index": 2},
        )
        result = await lesson_service.answer_item(self._fake_db(item), "l1", "i1", "u", "2")
        assert result["is_correct"] is True
        assert item.completed is True

    @pytest.mark.asyncio
    async def test_mc_item_records_self_rating_too(self):
        item = self._item(
            ItemType.grammar,
            data={"options": ["a", "b", "c", "d"], "correct_index": 1},
            correct_answer="b",
        )
        result = await lesson_service.answer_item(
            self._fake_db(item), "l1", "i1", "u", "1", self_rating=5
        )
        assert result["is_correct"] is True
        assert item.self_rating == 5

    @pytest.mark.asyncio
    async def test_mc_wrong_index_grades_wrong(self):
        # The generator sets `correct_answer` to the correct option text.
        item = self._item(
            ItemType.reading,
            data={"options": ["a", "b", "c", "d"], "correct_index": 2},
            correct_answer="c",
        )
        result = await lesson_service.answer_item(self._fake_db(item), "l1", "i1", "u", "1")
        assert result["is_correct"] is False
        assert result["correct_answer"] == "c"

    @pytest.mark.asyncio
    async def test_structured_flashcard_keeps_self_rating(self):
        item = self._item(
            ItemType.flashcard,
            data={"term": "家族", "reading": "かぞく", "definition": "family", "example": ""},
        )
        result = await lesson_service.answer_item(
            self._fake_db(item), "l1", "i1", "u", "", self_rating=4
        )
        assert result["is_correct"] is True
        assert item.self_rating == 4

    @pytest.mark.asyncio
    async def test_old_item_without_data_keeps_exact_match(self):
        item = self._item(ItemType.reading, data=None, correct_answer="家族")
        result = await lesson_service.answer_item(self._fake_db(item), "l1", "i1", "u", "家族")
        assert result["is_correct"] is True

    @pytest.mark.asyncio
    async def test_old_listening_keeps_keyword_grading(self):
        item = self._item(ItemType.listening, data=None, correct_answer="sunny weather")
        result = await lesson_service.answer_item(
            self._fake_db(item), "l1", "i1", "u", "It is sunny today"
        )
        assert result["is_correct"] is True
