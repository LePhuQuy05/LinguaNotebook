"""Lesson generation tests — chapter-driven composition (007-05).

Lessons with a curriculum map must come from one chapter (vocab +
exercises in book order), track document/chapter, and fall back to the
generic content-type retrieval when there is no map or no chunks yet.
"""

import types

import pytest

from src.models.learning import ItemType
from src.services import lesson_service
from src.services.lesson_service import _chapter_query, _next_chapter


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

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
    def __init__(self, structures=None, completed=None):
        self.structures = structures or []
        self.completed = completed or []
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
        return FakeResult([])

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


def _chapter(doc, num, title, start, end, order):
    return types.SimpleNamespace(
        document_id=doc, chapter_num=num, chapter_title=title,
        page_start=start, page_end=end, order=order,
    )


def _schedule(content_types=("vocabulary",), daily_item_count=4):
    return types.SimpleNamespace(
        id="s1", content_types=list(content_types), daily_item_count=daily_item_count,
    )


class TestNextChapter:
    @pytest.mark.asyncio
    async def test_returns_first_uncompleted_chapter(self):
        db = FakeDB(
            structures=[_chapter("d1", 1, "人・体", 2, 5, 0),
                        _chapter("d1", 2, "天気", 6, 9, 1)],
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
            return {"results": [
                {"chunk_id": f"c{i}", "content": f"内容{i}",
                 "document_id": "d1", "block_type": "paragraph",
                 "language": "ja", "difficulty": "intermediate",
                 "page_start": page, "chunk_index": idx, "score": 1.0}
                for i, (page, idx) in enumerate([(6, 0), (7, 1), (9, 2)])
            ]}

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
            db, "u", _schedule(content_types=["vocabulary", "grammar"], daily_item_count=3),
            types.SimpleNamespace(),
        )

        # Item types follow the schedule, round-robin over the chapter's
        # chunks in book order (vocabulary → flashcard).
        items = [a for a in db.added if type(a).__name__ == "LessonItem"]
        assert [i.item_type for i in items] == [
            ItemType.flashcard, ItemType.grammar, ItemType.flashcard,
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
