"""RAG service — hybrid search with RRF fusion."""

import logging

from qdrant_client.models import Filter, FieldCondition, MatchValue

from src.core.qdrant import qdrant_client, get_collection_name, ensure_collection
from src.services.embed_service import generate_embeddings, generate_sparse_vectors

logger = logging.getLogger(__name__)

RRF_K = 60


async def hybrid_search(
    user_id: str,
    query: str,
    language: str | None = None,
    block_type: str | None = None,
    difficulty: str | None = None,
    document_id: str | None = None,
    limit: int = 10,
) -> dict:
    """Hybrid search: dense + sparse vectors with RRF fusion and metadata filtering.

    Returns {"results": [...], "took_ms": float}
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
        must_conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))

    query_filter = Filter(must=must_conditions) if must_conditions else None

    # Generate query vectors
    dense_vector = generate_embeddings([query])[0]
    sparse_vector = generate_sparse_vectors([query])[0]

    # Dense search
    dense_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=("dense", dense_vector),
        query_filter=query_filter,
        limit=limit * 2,
    )

    # Sparse search
    sparse_results = qdrant_client.search(
        collection_name=collection_name,
        query_vector=("sparse", sparse_vector),
        query_filter=query_filter,
        limit=limit * 2,
    )

    # RRF fusion
    scores: dict[str, float] = {}
    payloads: dict[str, dict] = {}
    for rank, hit in enumerate(dense_results):
        rid = str(hit.id)
        scores[rid] = scores.get(rid, 0) + 1.0 / (RRF_K + rank + 1)
        payloads[rid] = hit.payload or {}
    for rank, hit in enumerate(sparse_results):
        rid = str(hit.id)
        scores[rid] = scores.get(rid, 0) + 1.0 / (RRF_K + rank + 1)
        payloads[rid] = hit.payload or {}

    # Sort by fused score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:limit]

    results = []
    for point_id, score in ranked:
        payload = payloads.get(point_id, {})
        results.append({
            "chunk_id": point_id,
            "content": payload.get("content", ""),
            "document_id": payload.get("document_id", ""),
            "block_type": payload.get("block_type", ""),
            "language": payload.get("language", ""),
            "difficulty": payload.get("difficulty", ""),
            "score": round(score, 4),
        })

    took_ms = (time.time() - t0) * 1000
    return {"results": results, "took_ms": round(took_ms, 2)}
