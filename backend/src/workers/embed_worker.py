"""Celery worker for embedding generation and Qdrant indexing."""

import json
import logging
import time
from datetime import UTC, datetime

from src.core.redis import redis_client

# Import every model so SQLAlchemy's mapper is fully configured as soon as
# this module loads. Document.user_id is a string FK to "users"; if the
# User model is never imported (a fresh process running only embed tasks)
# the mapper can't resolve it and every embed crashes with
# NoReferencedTableError before reaching the DB. A lazy import inside
# _run() would register them too, but module-level makes it a module
# invariant — and lets a regression test assert it in a fresh process.
from src.models.document import ContentBlock, Document, EmbedStatus
from src.models.knowledge_segment import KnowledgeSegment  # noqa: F401
from src.models.learning import Lesson, LessonItem  # noqa: F401
from src.models.schedule import Schedule  # noqa: F401
from src.models.srs import SRSCard  # noqa: F401
from src.models.sync import Device, ProgressSnapshot, SyncLog  # noqa: F401
from src.models.user import User  # noqa: F401
from src.services.embed_service import embed_and_index_chunks
from src.services.parser_service import (
    REDIS_EMBED_PROGRESS_PREFIX,
    REDIS_EMBED_PROGRESS_TTL,
)
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

    Progress is published to Redis under ``embed:progress:<doc_id>``
    (mirroring ``parse:progress:<doc_id>``) so the API can poll it; the
    document's ``embed_status``/``chunks_count`` columns are updated on
    success and set to ``embed_failed`` on error.
    """
    from sqlalchemy import select

    # AsyncSessionLocal stays lazy: tests monkeypatch it on its source
    # module, and a module-level binding would pin the unpatched object.
    from src.core.database import AsyncSessionLocal

    async def _publish(progress: dict) -> None:
        """Write one embed-progress frame to Redis (refresh TTL each batch)."""
        key = f"{REDIS_EMBED_PROGRESS_PREFIX}{document_id}"
        await redis_client.setex(
            key, REDIS_EMBED_PROGRESS_TTL, json.dumps(progress)
        )

    async def _run():
        nonlocal user_id
        started = time.monotonic()
        try:
            async with AsyncSessionLocal() as db:
                if user_id is None:
                    doc = (
                        await db.execute(
                            select(Document).where(Document.id == document_id)
                        )
                    ).scalar_one_or_none()
                    if not doc:
                        logger.warning(f"No document found for {document_id}")
                        return {"status": "skipped", "reason": "no document"}
                    user_id = doc.user_id
                else:
                    doc = (
                        await db.execute(
                            select(Document).where(Document.id == document_id)
                        )
                    ).scalar_one_or_none()

                doc.embed_status = EmbedStatus.embedding
                await db.commit()  # visible to the API during the long encode

                # Fetch all blocks for the document
                result = await db.execute(
                    select(ContentBlock)
                    .where(ContentBlock.document_id == document_id)
                    .order_by(ContentBlock.page_number, ContentBlock.created_at)
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

                # Embed and index; publish progress after each upsert batch
                async def _progress(frame: dict) -> None:
                    await _publish(
                        {
                            **frame,
                            "elapsed_sec": round(time.monotonic() - started, 1),
                        }
                    )

                await _publish(
                    {"status": "embedding", "current_chunks": 0, "total_chunks": 0}
                )
                count = await embed_and_index_chunks(
                    user_id=user_id,
                    document_id=document_id,
                    chunks=chunks,
                    progress_callback=_progress,
                )

                # Success: record durable state on the document
                doc.embed_status = EmbedStatus.embedded
                doc.chunks_count = count
                doc.embedded_at = datetime.now(UTC)
                await db.commit()

                await _publish(
                    {
                        "status": "embedded",
                        "chunks_indexed": count,
                        "elapsed_sec": round(time.monotonic() - started, 1),
                    }
                )
                logger.info(
                    f"Document {document_id}: {len(blocks)} blocks → {count} chunks indexed"
                )
                return {"status": "completed", "blocks": len(blocks), "chunks_indexed": count}

        except Exception as exc:
            logger.exception(f"Embed failed for document {document_id}")
            async with AsyncSessionLocal() as db:
                doc = (
                    await db.execute(
                        select(Document).where(Document.id == document_id)
                    )
                ).scalar_one_or_none()
                if doc is not None:
                    doc.embed_status = EmbedStatus.embed_failed
                    await db.commit()
            await _publish(
                {
                    "status": "embed_failed",
                    "error": str(exc),
                    "elapsed_sec": round(time.monotonic() - started, 1),
                }
            )
            raise

    return get_event_loop().run_until_complete(_run())
