"""hybrid_search tests — qdrant-client 1.18 query_points API + payloads.

Two things to pin: (1) search now uses ``query_points`` with prefetches and
RRF fusion — the old ``search()`` was removed in qdrant-client >= 1.15, so
this test would fail loudly if anyone reintroduces it; (2) every result must
carry ``page_end`` and ``token_count`` from the payload, which the daily
lesson source attribution and the curriculum chapter scoping depend on.
"""

import asyncio

import pytest
from qdrant_client.models import Fusion, Range

from src.services import rag_service


class FakeHit:
    def __init__(self, point_id, payload, score):
        self.id = point_id
        self.payload = payload
        self.score = score


class FakeResp:
    def __init__(self, points):
        self.points = points


def _payload(**overrides):
    payload = {
        "content": "天気",
        "document_id": "d1",
        "block_type": "paragraph",
        "language": "ja",
        "difficulty": "intermediate",
        "page_start": 6,
        "chunk_index": 0,
        "token_count": 42,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def env(monkeypatch):
    """Mock every external touchpoint so the test hits only the search path."""
    monkeypatch.setattr(rag_service, "ensure_collection", lambda user_id: None)
    monkeypatch.setattr(rag_service, "get_collection_name", lambda user_id: "c")
    monkeypatch.setattr(
        rag_service, "generate_embeddings", lambda texts, **k: [[0.1] * 4] * len(texts)
    )
    monkeypatch.setattr(
        rag_service,
        "generate_sparse_vectors",
        lambda texts: [{"indices": [0], "values": [1.0]}] * len(texts),
    )
    return {}


def _stub_query_points(monkeypatch, captured, points):
    def fake_query_points(**kwargs):
        captured.update(kwargs)
        return FakeResp(points)

    monkeypatch.setattr(rag_service.qdrant_client, "query_points", fake_query_points)


def test_results_carry_page_end_and_token_count(env, monkeypatch):
    captured = {}
    _stub_query_points(
        monkeypatch,
        captured,
        [FakeHit("p1", _payload(page_end=9), 0.8)],
    )

    out = asyncio.run(rag_service.hybrid_search("u", "天気"))

    result = out["results"][0]
    assert result["page_start"] == 6
    assert result["page_end"] == 9
    assert result["token_count"] == 42
    assert result["document_id"] == "d1"
    assert result["score"] == 0.8


def test_page_end_defaults_to_page_start_when_missing(env, monkeypatch):
    """Payloads written by older embeds may lack the page_end key entirely
    (a None value is different — .get returns the default only on a miss)."""
    payload = _payload()
    del payload["token_count"]
    _stub_query_points(monkeypatch, {}, [FakeHit("p1", payload, 0.5)])

    out = asyncio.run(rag_service.hybrid_search("u", "x"))

    assert out["results"][0]["page_end"] == 6
    assert out["results"][0]["token_count"] is None


def test_uses_query_points_with_rrf_fusion(env, monkeypatch):
    captured = {}
    _stub_query_points(monkeypatch, captured, [])

    asyncio.run(rag_service.hybrid_search("u", "query"))

    # The removed `search()` raised AttributeError; this pins the new shape.
    assert captured["query"].fusion == Fusion.RRF
    assert [p.using for p in captured["prefetch"]] == ["dense", "sparse"]
    assert captured["limit"] == 10
    assert captured["with_payload"] is True


def test_page_range_filter_forwarded_to_prefetch(env, monkeypatch):
    """Curriculum chapters search scoped to page_start..page_end."""
    captured = {}
    _stub_query_points(monkeypatch, captured, [])

    asyncio.run(rag_service.hybrid_search("u", "q", page_start=6, page_end=9))

    prefetch = captured["prefetch"][0]
    condition = prefetch.filter.must[0]
    assert condition.key == "page_start"
    assert condition.range == Range(gte=6, lte=9)


class FakePoint:
    def __init__(self, point_id, payload):
        self.id = point_id
        self.payload = payload


class TestGetChunkSources:
    def test_shapes_payloads_for_lesson_attribution(self, monkeypatch):
        points = [
            FakePoint("chunk-1", {
                "content": "天気の言葉",
                "document_id": "d1",
                "block_type": "paragraph",
                "page_start": 6,
                "token_count": 33,
            }),
            FakePoint("chunk-2", {
                "content": "身体の言葉",
                "document_id": "d1",
                "block_type": "list",
                "page_start": 7,
                "page_end": 8,
                "token_count": 10,
            }),
        ]
        captured = {}
        monkeypatch.setattr(
            rag_service.qdrant_client, "retrieve",
            lambda **kw: captured.update(kw) or points,
        )

        sources = rag_service.get_chunk_sources("u", ["chunk-1", "chunk-2"])

        assert captured["collection_name"] == "user_u"  # get_collection_name format
        assert captured["with_payload"] is True
        assert captured["with_vectors"] is False
        assert sources["chunk-1"]["page_start"] == 6
        # no page_end in payload → defaults to page_start
        assert sources["chunk-1"]["page_end"] == 6
        assert sources["chunk-1"]["content"] == "天気の言葉"
        assert sources["chunk-2"]["page_end"] == 8
        assert sources["chunk-2"]["block_type"] == "list"

    def test_empty_ids_skips_retrieve(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            rag_service.qdrant_client, "retrieve",
            lambda **kw: called.append(kw) or [],
        )

        assert rag_service.get_chunk_sources("u", []) == {}
        assert called == []
