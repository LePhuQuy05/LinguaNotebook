"""RAG API endpoints — hybrid search."""

from fastapi import APIRouter, Depends, Query

from src.core.dependencies import get_current_user_id
from src.services import rag_service

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    language: str | None = Query(None),
    block_type: str | None = Query(None),
    difficulty: str | None = Query(None),
    document_id: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Depends(get_current_user_id),
):
    """Hybrid search across user's knowledge base."""
    return await rag_service.hybrid_search(
        user_id=user_id,
        query=q,
        language=language,
        block_type=block_type,
        difficulty=difficulty,
        document_id=document_id,
        limit=limit,
    )


@router.get("/chunks/{chunk_id}")
async def get_chunk(
    chunk_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a single knowledge segment's Qdrant payload by point ID."""
    from src.core.qdrant import qdrant_client, get_collection_name

    collection = get_collection_name(user_id)
    try:
        results = qdrant_client.retrieve(
            collection_name=collection,
            ids=[chunk_id],
            with_payload=True,
            with_vectors=False,
        )
        if not results:
            return {"chunk_id": chunk_id, "found": False}
        return {"chunk_id": chunk_id, "found": True, "payload": results[0].payload}
    except Exception:
        return {"chunk_id": chunk_id, "found": False}
