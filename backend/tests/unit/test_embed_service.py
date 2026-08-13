"""Embed service payload tests — Qdrant points carry real page ranges.

The regression: every point claimed page_start: 1 because the chunker
never received page numbers. Chunk metadata must flow into the payload.
"""

import asyncio

from src.utils.chunker import Chunk


def _chunk(page_start: int = 1, page_end: int | None = None) -> Chunk:
    return Chunk(
        content="テキスト",
        source_block_ids=["b1"],
        block_type="paragraph",
        chunk_index=0,
        token_count=10,
        language="ja",
        metadata={"page_start": page_start, "page_end": page_end or page_start},
    )


def test_payload_carries_page_range(monkeypatch):
    import src.services.embed_service as es

    captured = {}
    monkeypatch.setattr(
        es, "generate_embeddings", lambda texts, **k: [[0.1] * 4] * len(texts)
    )
    monkeypatch.setattr(
        es,
        "generate_sparse_vectors",
        lambda texts: [{"indices": [0], "values": [1.0]}] * len(texts),
    )
    monkeypatch.setattr(es, "ensure_collection", lambda user_id: None)
    monkeypatch.setattr(es, "get_collection_name", lambda user_id: "c")
    monkeypatch.setattr(
        es.qdrant_client, "upsert",
        lambda collection_name, points: captured.update(points=points),
    )

    asyncio.run(es.embed_and_index_chunks("u", "d", [_chunk(4, 5)]))

    payload = captured["points"][0]["payload"]
    assert payload["page_start"] == 4
    assert payload["page_end"] == 5
    assert payload["content"] == "テキスト"
    assert payload["document_id"] == "d"


def test_single_page_chunk_reports_same_start_and_end(monkeypatch):
    import src.services.embed_service as es

    captured = {}
    monkeypatch.setattr(
        es, "generate_embeddings", lambda texts, **k: [[0.1] * 4] * len(texts)
    )
    monkeypatch.setattr(
        es,
        "generate_sparse_vectors",
        lambda texts: [{"indices": [0], "values": [1.0]}] * len(texts),
    )
    monkeypatch.setattr(es, "ensure_collection", lambda user_id: None)
    monkeypatch.setattr(es, "get_collection_name", lambda user_id: "c")
    monkeypatch.setattr(
        es.qdrant_client, "upsert",
        lambda collection_name, points: captured.update(points=points),
    )

    asyncio.run(es.embed_and_index_chunks("u", "d", [_chunk(3)]))

    payload = captured["points"][0]["payload"]
    assert payload["page_start"] == 3
    assert payload["page_end"] == 3


def _patch_qdrant(monkeypatch, es):
    """Common mocks: no model loading, no real Qdrant, record upserts."""
    captured = {"points": []}
    monkeypatch.setattr(
        es, "generate_embeddings", lambda texts, **k: [[0.1] * 4] * len(texts)
    )
    monkeypatch.setattr(
        es,
        "generate_sparse_vectors",
        lambda texts: [{"indices": [0], "values": [1.0]}] * len(texts),
    )
    monkeypatch.setattr(es, "ensure_collection", lambda user_id: None)
    monkeypatch.setattr(es, "get_collection_name", lambda user_id: "c")
    monkeypatch.setattr(
        es.qdrant_client, "upsert",
        lambda collection_name, points: captured["points"].extend(points),
    )
    return captured


def test_progress_callback_fires_initial_then_per_batch(monkeypatch):
    import src.services.embed_service as es

    captured = _patch_qdrant(monkeypatch, es)
    frames = []

    async def record(frame):
        frames.append(frame)

    # 450 chunks → 3 upsert batches (200 + 200 + 50): the callback must
    # fire once before the loop and once after each batch.
    chunks = [_chunk(i) for i in range(450)]

    asyncio.run(es.embed_and_index_chunks("u", "d", chunks, progress_callback=record))

    assert [f["current_chunks"] for f in frames] == [0, 200, 400, 450]
    assert all(f["status"] == "embedding" for f in frames)
    assert all(f["total_chunks"] == 450 for f in frames)
    # 3 upsert batches really happened
    assert len(captured["points"]) == 450


def test_returns_indexed_count_without_callback(monkeypatch):
    import src.services.embed_service as es

    captured = _patch_qdrant(monkeypatch, es)

    count = asyncio.run(
        es.embed_and_index_chunks("u", "d", [_chunk(1), _chunk(2), _chunk(3)])
    )

    assert count == 3
    assert len(captured["points"]) == 3
