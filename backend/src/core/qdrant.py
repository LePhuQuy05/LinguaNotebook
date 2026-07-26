"""Qdrant client and collection management."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams

from src.core.config import settings

qdrant_client = QdrantClient(url=settings.qdrant_url)

COLLECTION_PREFIX = "user_"
VECTOR_SIZE = 1024  # BGE-M3 embedding dimension


def get_collection_name(user_id: str) -> str:
    """Per-user collection for hardware-enforced data isolation."""
    return f"{COLLECTION_PREFIX}{user_id.replace('-', '_')}"


def ensure_collection(user_id: str) -> None:
    """Create user's Qdrant collection if it doesn't exist."""
    name = get_collection_name(user_id)
    if not qdrant_client.collection_exists(name):
        qdrant_client.create_collection(
            collection_name=name,
            vectors_config={"dense": VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
        )


def delete_collection(user_id: str) -> None:
    """Delete user's collection (on account deletion)."""
    name = get_collection_name(user_id)
    if qdrant_client.collection_exists(name):
        qdrant_client.delete_collection(name)


async def check_qdrant() -> str:
    """Health check: verify Qdrant connectivity."""
    try:
        qdrant_client.get_collections()
        return "connected"
    except Exception as e:
        return f"error: {e}"
