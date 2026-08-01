"""Parser service plumbing tests (spec 006, ticket 04).

Guards ticket acceptance criterion 3: the API keeps accepting `mode` and
the service forwards it to the worker task without breaking — the worker
ignores the value (routing is decided by the text-layer check), but the
dispatch chain must keep carrying it for backward compatibility.
"""

import asyncio

import pytest

from src.services import parser_service


class FakeSession:
    """Minimal AsyncSession: records adds, commits and refreshes as no-ops."""

    def __init__(self):
        self.added: list = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass


@pytest.fixture
def fake_delay(monkeypatch):
    """Replace the Celery task's .delay with a recorder."""
    calls: list = []

    def fake_delay(*args, **kwargs):
        calls.append((args, kwargs))
        return object()

    from src.workers.parse_worker import parse_pdf_task
    monkeypatch.setattr(parse_pdf_task, "delay", fake_delay)
    return calls


@pytest.fixture
def stub_storage(monkeypatch):
    """Skip the real S3 upload inside create_document."""
    monkeypatch.setattr(parser_service, "upload_file", lambda *a, **k: None)


def test_create_document_forwards_parse_mode_to_worker(fake_delay, stub_storage):
    doc = asyncio.run(parser_service.create_document(
        db=FakeSession(),
        user_id="u1",
        filename="book.pdf",
        file_data=b"%PDF-1.4 fake",
        mime_type="application/pdf",
        parse_mode="hybrid",
    ))

    assert doc.status.value == "queued"
    (args, kwargs) = fake_delay[0]
    assert args[:5] == (doc.id, f"documents/u1/{doc.id}/book.pdf", 100, 1, None)
    assert kwargs == {"parse_mode": "hybrid"}


def test_create_document_defaults_parse_mode_to_fast(fake_delay, stub_storage):
    asyncio.run(parser_service.create_document(
        db=FakeSession(),
        user_id="u1",
        filename="book.pdf",
        file_data=b"%PDF-1.4 fake",
        mime_type="application/pdf",
    ))

    assert fake_delay[0][1] == {"parse_mode": "fast"}
