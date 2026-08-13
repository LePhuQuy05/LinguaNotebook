"""RAG service — hybrid search with RRF fusion."""

import logging

from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    Range,
)

from src.core.qdrant import ensure_collection, get_collection_name, qdrant_client
from src.services.embed_service import generate_embeddings, generate_sparse_vectors

logger = logging.getLogger(__name__)

# Qdrant Range bounds must be concrete. When only one of page_start /
# page_end is given, the other side is clamped to these sentinels
# ("page 1" and "a page beyond any real document").
MIN_PAGE = 1
MAX_PAGE = 10**6


async def hybrid_search(
    user_id: str,
    query: str,
    language: str | None = None,
    block_type: str | None = None,
    difficulty: str | None = None,
    document_id: str | None = None,
    page_start: int | None = None,
    page_end: int | None = None,
    limit: int = 10,
) -> dict:
    """Hybrid search: dense + sparse vectors with RRF fusion and metadata filtering.

    `page_start`/`page_end` restrict results to chunks whose first page
    falls inside the range (curriculum chapters). Returns
    {"results": [...], "took_ms": float}.
    """
    import time
    t0 = time.time()

    ensure_collection(user_id)
    collection_name = get_collection_name(user_id)

    # Build metadata filter
    must_conditions = []
    if language:
        must_conditions.append(FieldCondition(key="language", match=MatchValue(value=language)))
    if block_type:
        must_conditions.append(FieldCondition(key="block_type", match=MatchValue(value=block_type)))
    if difficulty:
        must_conditions.append(FieldCondition(key="difficulty", match=MatchValue(value=difficulty)))
    if document_id:
        must_conditions.append(
            FieldCondition(key="document_id", match=MatchValue(value=document_id))
        )
    if page_start is not None or page_end is not None:
        must_conditions.append(FieldCondition(
            key="page_start",
            range=Range(
                gte=page_start if page_start is not None else MIN_PAGE,
                lte=page_end if page_end is not None else MAX_PAGE,
            ),
        ))

    query_filter = Filter(must=must_conditions) if must_conditions else None

    # Generate query vectors
    dense_vector = generate_embeddings([query])[0]
    sparse_vector = generate_sparse_vectors([query])[0]

    # Hybrid search: dense + sparse prefetches fused server-side with RRF.
    # qdrant-client >=1.15 removed `search` in favour of `query_points` with
    # prefetch + FusionQuery — one round-trip, fusion done by Qdrant.
    resp = qdrant_client.query_points(
        collection_name=collection_name,
        prefetch=[
            Prefetch(
                query=dense_vector,
                using="dense",
                filter=query_filter,
                limit=limit * 2,
            ),
            Prefetch(
                query=sparse_vector,
                using="sparse",
                filter=query_filter,
                limit=limit * 2,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )

    results = []
    for hit in resp.points:
        payload = hit.payload or {}
        results.append({
            "chunk_id": str(hit.id),
            "content": payload.get("content", ""),
            "document_id": payload.get("document_id", ""),
            "block_type": payload.get("block_type", ""),
            "language": payload.get("language", ""),
            "difficulty": payload.get("difficulty", ""),
            "page_start": payload.get("page_start", 0),
            "page_end": payload.get("page_end", payload.get("page_start", 0)),
            "chunk_index": payload.get("chunk_index", 0),
            "token_count": payload.get("token_count"),
            "score": round(hit.score, 4),
        })

    took_ms = (time.time() - t0) * 1000
    return {"results": results, "took_ms": round(took_ms, 2)}


def get_chunk_sources(user_id: str, source_ids: list[str]) -> dict[str, dict]:
    """Fetch Qdrant payloads by point id and shape them for lesson-source
    attribution (page range, token count, block type, content).

    Used by the daily-lesson endpoint to show where each item came from.
    Unknown ids are simply absent from the result.
    """
    if not source_ids:
        return {}
    points = qdrant_client.retrieve(
        collection_name=get_collection_name(user_id),
        ids=source_ids,
        with_payload=True,
        with_vectors=False,
    )
    sources = {}
    for p in points:
        payload = p.payload or {}
        sources[p.id] = {
            "page_start": payload.get("page_start"),
            "page_end": payload.get("page_end", payload.get("page_start")),
            "token_count": payload.get("token_count"),
            "block_type": payload.get("block_type", ""),
            "document_id": payload.get("document_id", ""),
            "content": payload.get("content", ""),
        }
    return sources
