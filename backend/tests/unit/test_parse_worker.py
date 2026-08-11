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
