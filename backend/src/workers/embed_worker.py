"""Celery worker for embedding generation and Qdrant indexing."""

import logging

from src.workers.celery_app import celery_app
from src.utils.chunker import SmartChunker
from src.services.embed_service import embed_and_index_chunks

logger = logging.getLogger(__name__)


@celery_app.task(name="embed_document", bind=True, max_retries=3)
def embed_document_task(self, document_id: str, user_id: str) -> dict:
    """Chunk parsed document content and index in Qdrant.

    Triggered after parse completes. Reads ContentBlocks from DB,
    chunks them, generates embeddings, and upserts to Qdrant.
    """
    import asyncio
    from sqlalchemy import select
    from src.core.database import AsyncSessionLocal
    from src.models.document import ContentBlock

    async def _run():
        async with AsyncSessionLocal() as db:
            # Fetch all blocks for the document
            result = await db.execute(
                select(ContentBlock).where(ContentBlock.document_id == document_id).order_by(
                    ContentBlock.page_number, ContentBlock.created_at
                )
            )
            blocks = result.scalars().all()

            if not blocks:
                logger.warning(f"No blocks found for document {document_id}")
                return {"status": "skipped", "reason": "no blocks"}

            # Convert to dicts for chunker
            block_dicts = [
                {
                    "id": b.id,
                    "block_type": b.block_type.value,
                    "content_markdown": b.content_markdown,
                }
                for b in blocks
            ]

            # Chunk
            chunker = SmartChunker()
            language = blocks[0].language if blocks else "en"
            chunks = chunker.chunk_blocks(block_dicts, language=language)

            # Embed and index
            count = await embed_and_index_chunks(
                user_id=user_id,
                document_id=document_id,
                chunks=chunks,
            )

            logger.info(f"Document {document_id}: {len(blocks)} blocks → {count} chunks indexed")
            return {"status": "completed", "blocks": len(blocks), "chunks_indexed": count}

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
