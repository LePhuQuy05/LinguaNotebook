"""Worker block-saving path tests.

The regression this ticket fixed lived in `_save_content_blocks`: the old
regex split discarded the `--- Page N ---` marker numbers and indexed the
array instead, so a 5-page PDF stored blocks as pages 2-6 and `total_pages`
came from counting non-blank split chunks. These tests pin the worker glue
itself (not just the pure parser service) to the ticket's contract.
"""

import pytest

FIVE_PAGE_MARKDOWN = (
    "\n--- Page 1 ---\n表紙"
    "\n--- Page 2 ---\nはじめに\n\n本文です。"
    "\n--- Page 3 ---\n| a | b |\n| --- | --- |\n| c | d |"
    "\n--- Page 4 ---\n・りんご\n・みかん"
    "\n--- Page 5 ---\n最終ページです。"
)


class FakeResult:
    def __init__(self, doc):
        self._doc = doc

    def scalar_one_or_none(self):
        return self._doc


class FakeDocument:
    language = "ja"
    status = None
    total_pages = None
    parse_method = None
    parsed_content_path = None


class FakeSession:
    """Stand-in for AsyncSessionLocal: records added objects, fakes commit."""

    def __init__(self, doc):
        self._doc = doc
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, statement):
        return FakeResult(self._doc)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass


@pytest.fixture
def worker(monkeypatch):
    import src.workers.parse_worker as pw

    sessions = {}

    def fake_factory():
        doc = FakeDocument()
        session = FakeSession(doc)
        sessions["doc"] = doc
        sessions["session"] = session
        return session

    # The function binds AsyncSessionLocal at call time from its source
    # module — patch there, not on the worker module.
    monkeypatch.setattr("src.core.database.AsyncSessionLocal", fake_factory)
    return pw, sessions


class TestSaveContentBlocks:
    def test_blocks_labeled_with_real_page_numbers(self, worker):
        """Regression: a 5-page PDF must store pages 1-5, not 2-6."""
        pw, sessions = worker
        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")

        pages = [b.page_number for b in sessions["session"].added]
        assert pages == [1, 2, 2, 3, 4, 5]

    def test_block_types_mapped_to_enum(self, worker):
        pw, sessions = worker
        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")

        types = [b.block_type.value for b in sessions["session"].added]
        assert types == ["header", "header", "paragraph", "table", "list", "paragraph"]

    def test_total_pages_is_highest_parsed_page(self, worker):
        pw, sessions = worker
        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")

        assert sessions["doc"].total_pages == 5

    def test_total_pages_counts_blank_last_page(self, worker):
        """A blank page 5 still contributes: total_pages must be 5, not 4."""
        pw, sessions = worker
        markdown = (
            "\n--- Page 1 ---\n本文。"
            "\n--- Page 2 ---\n\n"
            "\n--- Page 3 ---\n\n"
            "\n--- Page 4 ---\n\n"
            "\n--- Page 5 ---\n\n"
        )
        pw._save_content_blocks("doc-1", markdown, [], "ocr")

        assert sessions["doc"].total_pages == 5
        # only the non-blank page yields blocks
        assert [b.page_number for b in sessions["session"].added] == [1]

    def test_no_tag_or_coordinate_noise(self, worker):
        pw, sessions = worker
        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")

        for b in sessions["session"].added:
            assert "<BLOCK>" not in b.content_markdown
            assert b.bbox is None

    def test_unknown_block_type_falls_back_to_paragraph(self, worker, monkeypatch):
        from src.services.hpd_markdown import Block

        pw, sessions = worker
        # The worker binds the function lazily from its source module —
        # patch there, not on the worker module.
        monkeypatch.setattr(
            "src.services.hpd_markdown.markdown_to_block_records",
            lambda markdown: [(7, Block(block_type="mystery", content="x"))],
        )
        pw._save_content_blocks("doc-1", "anything", [], "ocr")

        assert sessions["session"].added[0].block_type.value == "paragraph"
        assert sessions["session"].added[0].page_number == 7

    def test_status_reflects_errors(self, worker):
        pw, sessions = worker
        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [(3, "boom")], "ocr")

        assert sessions["doc"].status.value == "completed_with_errors"
        assert sessions["doc"].parse_method == "ocr"


class TestContentBlocksIdempotency:
    """A re-parse must replace a document's blocks, never duplicate them.

    The old code only added new ContentBlock rows, so re-running the parse
    task for a document stacked a second (garbage) copy of every page. The
    save now deletes the document's existing blocks first — in the same
    transaction, so a crash mid-save leaves the old blocks intact."""

    class IdempotentSession:
        def __init__(self, doc):
            self._doc = doc
            self.added = []
            self.deletes = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute(self, statement):
            from sqlalchemy import Delete

            if isinstance(statement, Delete):
                self.deletes += 1
                return FakeResult(None)
            return FakeResult(self._doc)

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            pass

    def test_reparse_replaces_existing_blocks(self, worker, monkeypatch):
        pw, _ = worker
        doc = FakeDocument()
        session = self.IdempotentSession(doc)
        monkeypatch.setattr("src.core.database.AsyncSessionLocal", lambda: session)

        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")

        # old blocks deleted first, then the fresh batch
        assert session.deletes == 1
        assert len(session.added) == 6


class TestSaveCurriculumStructure:
    """TOC extraction wiring — rows are replaced on re-parse, never merged,
    and an absent map writes nothing (conservative by design)."""

    class CurriculumSession:
        def __init__(self):
            self.added = []
            self.deletes = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute(self, statement):
            from sqlalchemy import Delete

            if isinstance(statement, Delete):
                self.deletes += 1
            return FakeResult(None)

        def add(self, obj):
            self.added.append(obj)

        async def commit(self):
            pass

    @pytest.fixture
    def curriculum_env(self, worker, monkeypatch):
        """Patch the session factory at its source, after `worker`'s patch,
        so ours wins; return the worker module too."""
        pw, _ = worker
        session = self.CurriculumSession()
        monkeypatch.setattr("src.core.database.AsyncSessionLocal", lambda: session)
        return pw, session

    def test_replaces_rows_on_reparse(self, monkeypatch, curriculum_env):
        pw, session = curriculum_env
        monkeypatch.setattr(
            "src.services.curriculum_service.extract_curriculum",
            lambda markdown: [
                {
                    "part": "第1部",
                    "chapter_num": 1,
                    "chapter_title": "人・体",
                    "page_start": 2,
                    "page_end": 5,
                },
                {
                    "part": "第1部",
                    "chapter_num": 2,
                    "chapter_title": "天気",
                    "page_start": 6,
                    "page_end": 9,
                },
            ],
        )

        pw._save_curriculum_structure("doc-1", "any markdown")

        # old rows deleted first, then fresh rows with book order
        assert session.deletes == 1
        assert len(session.added) == 2
        assert [r.order for r in session.added] == [0, 1]
        assert session.added[0].chapter_num == 1
        assert session.added[0].document_id == "doc-1"
        assert session.added[0].page_end == 5

    def test_empty_map_writes_nothing(self, monkeypatch, curriculum_env):
        pw, session = curriculum_env
        monkeypatch.setattr(
            "src.services.curriculum_service.extract_curriculum",
            lambda markdown: [],
        )

        pw._save_curriculum_structure("doc-1", "no toc here")

        assert session.deletes == 0
        assert session.added == []


class TestPersistentEventLoop:
    """Regression: saves must run on one loop that lives for the process.

    The old code created a fresh `asyncio.new_event_loop()` per save call
    and closed it in a finally. The module-level async engine's asyncpg
    pool binds its connections to the loop that was running when they were
    created — a closed loop left them pointing at a dead proactor, and the
    *second* save in one worker process crashed with
    ``'NoneType' object has no attribute 'send'``
    (proactor_events.py `_loop._proactor.send`). Real failure: OCR doc
    parsed fine but every ContentBlock save failed after the first task
    had already used the pool.
    """

    def test_event_loop_is_persistent_across_calls(self, worker):
        pw, _ = worker

        assert pw._get_event_loop() is pw._get_event_loop()

    def test_parse_worker_uses_the_shared_worker_loop(self, worker):
        """All worker modules must share one loop per process."""
        from src.utils.worker_loop import get_event_loop

        pw, _ = worker
        assert pw._get_event_loop() is get_event_loop()


class TestEmbedDispatch:
    def test_dispatch_hands_document_to_embed_worker(self, worker, monkeypatch):
        import types

        import src.workers.embed_worker as ew

        pw, _ = worker
        calls = []
        recorder = types.SimpleNamespace(delay=lambda **kw: calls.append(kw))
        monkeypatch.setattr(ew, "embed_document_task", recorder)

        pw._dispatch_embed("doc-1")

        # user_id=None: the embed worker resolves it from the document
        assert calls == [{"document_id": "doc-1", "user_id": None}]

    def test_saves_run_on_the_persistent_loop(self, worker, monkeypatch):
        import asyncio

        pw, _ = worker

        class LoopRecordingSession(FakeSession):
            def __init__(self, doc, loops):
                super().__init__(doc)
                self._loops = loops

            async def commit(self):
                self._loops.append(asyncio.get_running_loop())

        loops = []

        def fake_factory():
            return LoopRecordingSession(FakeDocument(), loops)

        monkeypatch.setattr("src.core.database.AsyncSessionLocal", fake_factory)

        pw._save_content_blocks("doc-1", FIVE_PAGE_MARKDOWN, [], "ocr")
        pw._save_content_blocks("doc-2", FIVE_PAGE_MARKDOWN, [], "ocr")

        # Both saves ran on the SAME loop — the one that never gets closed.
        assert len(loops) == 2
        assert loops[0] is loops[1]
        assert loops[0] is pw._get_event_loop()
