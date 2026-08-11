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
