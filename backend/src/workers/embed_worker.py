"""Celery worker for embedding generation and Qdrant indexing."""

import logging

from src.services.embed_service import embed_and_index_chunks
from src.utils.chunker import SmartChunker
from src.utils.worker_loop import get_event_loop
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="embed_document", bind=True, max_retries=3)
def embed_document_task(self, document_id: str, user_id: str | None = None) -> dict:
    """Chunk parsed document content and index in Qdrant.

    Triggered after parse completes. Reads ContentBlocks from DB,
    chunks them, generates embeddings, and upserts to Qdrant. The
    user_id is resolved from the document when not passed (the parse
    worker dispatches without it — one less lookup there).

    Runs on the worker's persistent event loop (src.utils.worker_loop):
    the asyncpg pool binds to the loop that created its connections, and
    a per-call loop would crash the second document in one process with
    "proactor.send on None".
    """
    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.models.document import ContentBlock, Document

    async def _run():
        nonlocal user_id
        async with AsyncSessionLocal() as db:
            if user_id is None:
                doc = (
                    await db.execute(select(Document).where(Document.id == document_id))
                ).scalar_one_or_none()
                if not doc:
                    logger.warning(f"No document found for {document_id}")
                    return {"status": "skipped", "reason": "no document"}
                user_id = doc.user_id

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
                    "page_number": b.page_number,
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

    return get_event_loop().run_until_complete(_run())
