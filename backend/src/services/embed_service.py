"""Embedding service — BGE-M3 multilingual embeddings + Qdrant upsert."""

import logging
import uuid

from fastembed import SparseTextEmbedding
from sentence_transformers import SentenceTransformer

from src.core.qdrant import ensure_collection, get_collection_name, qdrant_client
from src.utils.chunker import Chunk

logger = logging.getLogger(__name__)

# Models loaded once at module level
_dense_model: SentenceTransformer | None = None
_sparse_model: SparseTextEmbedding | None = None


def _get_dense_model() -> SentenceTransformer:
    global _dense_model
    if _dense_model is None:
        logger.info("Loading BGE-M3 embedding model...")
        # Pinned to CPU: sentence-transformers auto-selects the Intel Arc
        # iGPU here, and the encode pass OOMs against its 16 GiB budget
        # (measured 2026-08-11: 52 GiB activation request). Background
        # indexing on CPU is slower but reliable — the iGPU stays
        # reserved for HPD OCR.
        _dense_model = SentenceTransformer("BAAI/bge-m3", device="cpu")
        logger.info("BGE-M3 ready")
    return _dense_model


def _get_sparse_model() -> SparseTextEmbedding:
    global _sparse_model
    if _sparse_model is None:
        logger.info("Loading BM25 sparse model...")
        _sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")
        logger.info("BM25 sparse model ready")
    return _sparse_model


def generate_embeddings(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Generate BGE-M3 dense embeddings for a list of texts."""
    model = _get_dense_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return embeddings.tolist()


def generate_sparse_vectors(texts: list[str]) -> list[dict]:
    """Generate BM25 sparse vectors for a list of texts."""
    model = _get_sparse_model()
    vectors = list(model.embed(texts))
    return [{"indices": v.indices.tolist(), "values": v.values.tolist()} for v in vectors]


async def embed_and_index_chunks(
    user_id: str,
    document_id: str,
    chunks: list[Chunk],
) -> int:
    """Embed chunks and upsert to user's Qdrant collection.

    Returns number of indexed points.
    """
    if not chunks:
        return 0

    ensure_collection(user_id)
    collection_name = get_collection_name(user_id)

    texts = [chunk.content for chunk in chunks]
    dense_vectors = generate_embeddings(texts)
    sparse_vectors = generate_sparse_vectors(texts)

    points = []
    for i, chunk in enumerate(chunks):
        point_id = str(uuid.uuid4())
        points.append({
            "id": point_id,
            "vector": {"dense": dense_vectors[i], "sparse": sparse_vectors[i]},
            "payload": {
                "user_id": user_id,
                "document_id": document_id,
                "block_type": chunk.block_type,
                "language": chunk.language,
                "difficulty": "intermediate",
                "page_start": chunk.metadata.get("page_start", 1),
                "page_end": chunk.metadata.get("page_end", chunk.metadata.get("page_start", 1)),
                "chunk_index": chunk.chunk_index,
                "token_count": chunk.token_count,
                "created_at": chunk.metadata.get("created_at", ""),
                "content": chunk.content,
            },
        })

    qdrant_client.upsert(collection_name=collection_name, points=points)
    logger.info(f"Indexed {len(points)} chunks for user {user_id}, document {document_id}")
    return len(points)
