"""Embed worker tests — user_id resolution + persistent loop.

The regression this pins: `embed_document` created a new event loop per
call and closed it in a finally — the second document in one worker
process crashed with "proactor.send on None" (asyncpg pool connections
bound to the dead loop). It must run on the shared persistent loop
(src.utils.worker_loop), and resolve user_id from the document when the
parse worker dispatches without it.
"""

import asyncio
import types

import pytest

import src.workers.embed_worker as ew
from src.utils.worker_loop import get_event_loop


class FakeBlock:
    def __init__(self, bid, content, page=1):
        self.id = bid
        self.block_type = types.SimpleNamespace(value="paragraph")
        self.content_markdown = content
        self.language = "ja"
        self.page_number = page


class FakeDoc:
    id = "doc-1"
    user_id = "user-9"


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return _FakeScalars(self._value)


class _FakeScalars:
    def __init__(self, items):
        self._items = items if isinstance(items, list) else [items]

    def all(self):
        return self._items


class FakeSession:
    """Dispatch on the queried table (the Document query is conditional)."""

    def __init__(self, doc, blocks, loops):
        self._doc = doc
        self._blocks = blocks
        self._loops = loops
        self._doc_queried = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, statement):
        self._loops.append(asyncio.get_running_loop())
        if self._doc_queried:
            return FakeResult(self._blocks)
        if statement.froms and statement.froms[0].name == "documents":
            self._doc_queried = True
            return FakeResult(self._doc)
        return FakeResult(self._blocks)


@pytest.fixture
def env(monkeypatch):
    """Install a fake session factory + embed/index recorder."""
    state = {"indexed": [], "loops": []}

    def fake_factory():
        session = FakeSession(FakeDoc(), [FakeBlock("b1", "テキスト")], state["loops"])
        state["session"] = session
        return session

    async def fake_embed_and_index(user_id, document_id, chunks):
        state["indexed"].append({
            "user_id": user_id,
            "document_id": document_id,
            "chunks": chunks,
        })
        return len(chunks)

    monkeypatch.setattr("src.core.database.AsyncSessionLocal", fake_factory)
    monkeypatch.setattr(ew, "embed_and_index_chunks", fake_embed_and_index)
    return state


def test_resolves_user_id_from_document(env):
    result = ew.embed_document_task(document_id="doc-1", user_id=None)

    assert result["status"] == "completed"
    assert env["indexed"][0]["user_id"] == "user-9"
    assert env["indexed"][0]["document_id"] == "doc-1"
    assert len(env["indexed"][0]["chunks"]) >= 1


def test_explicit_user_id_is_kept(env):
    ew.embed_document_task(document_id="doc-1", user_id="passed-user")

    assert env["indexed"][0]["user_id"] == "passed-user"


def test_runs_on_the_shared_persistent_loop(env):
    """Regression: per-call loops crash the second document in one process."""
    ew.embed_document_task(document_id="doc-1")
    ew.embed_document_task(document_id="doc-2")

    assert len(env["loops"]) == 4  # two selects per call
    assert all(loop is env["loops"][0] for loop in env["loops"])
    assert env["loops"][0] is get_event_loop()


def test_missing_document_skips(env, monkeypatch):
    class NoDocSession(FakeSession):
        def __init__(self, loops):
            super().__init__(FakeDoc(), [], loops)
            self._doc = None

    monkeypatch.setattr(
        "src.core.database.AsyncSessionLocal", lambda: NoDocSession(env["loops"])
    )

    result = ew.embed_document_task(document_id="ghost")

    assert result["status"] == "skipped"
    assert env["indexed"] == []
