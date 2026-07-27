"""Document parsing service — orchestrates upload, Celery job dispatch, and progress tracking."""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.redis import redis_client
from src.core.storage import upload_file
from src.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)

REDIS_PROGRESS_PREFIX = "parse:progress:"
REDIS_PROGRESS_TTL = 3600  # 1 hour


async def create_document(
    db: AsyncSession,
    user_id: str,
    filename: str,
    file_data: bytes,
    mime_type: str,
    language: str | None = None,
    dpi: int = 100,
    page_start: int = 1,
    page_end: int | None = None,
) -> Document:
    """Create a Document record and queue it for parsing."""
    # Validate file size
    max_size = 524_288_000  # 500MB
    if len(file_data) > max_size:
        raise ValueError(f"File exceeds maximum size of {max_size} bytes")

    doc_id = str(uuid.uuid4())
    object_key = f"documents/{user_id}/{doc_id}/{filename}"

    # Upload to storage
    upload_file(file_data, object_key, mime_type)

    # Create DB record
    document = Document(
        id=doc_id,
        user_id=user_id,
        filename=filename,
        file_path=object_key,
        file_size_bytes=len(file_data),
        mime_type=mime_type,
        language=language,
        dpi=dpi,
        status=DocumentStatus.queued,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    # Dispatch Celery task with page range
    from src.workers.parse_worker import parse_pdf_task
    parse_pdf_task.delay(doc_id, object_key, dpi, page_start, page_end)

    logger.info(f"Document {doc_id} queued for parsing: {filename}")
    return document


async def get_document(db: AsyncSession, document_id: str, user_id: str) -> Document | None:
    """Get a document by ID, scoped to user."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_documents(
    db: AsyncSession,
    user_id: str,
    status: DocumentStatus | None = None,
    language: str | None = None,
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Document], int]:
    """Paginated list of user's documents with optional filters."""
    query = select(Document).where(Document.user_id == user_id)

    if status:
        query = query.where(Document.status == status)
    if language:
        query = query.where(Document.language == language)

    # Count
    count_query = select(Document).where(Document.user_id == user_id)
    if status:
        count_query = count_query.where(Document.status == status)
    if language:
        count_query = count_query.where(Document.language == language)
    total_result = await db.execute(select(Document.id))
    total = len(total_result.scalars().all())  # Simplified — in production use func.count

    query = query.order_by(Document.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    documents = list(result.scalars().all())

    return documents, total


async def update_document(
    db: AsyncSession, document_id: str, user_id: str, **kwargs
) -> Document | None:
    """Update document metadata (language, tags)."""
    doc = await get_document(db, document_id, user_id)
    if doc is None:
        return None
    for key, value in kwargs.items():
        if hasattr(doc, key) and value is not None:
            setattr(doc, key, value)
    await db.commit()
    await db.refresh(doc)
    return doc


async def delete_document(db: AsyncSession, document_id: str, user_id: str) -> bool:
    """Delete a document and its parsed content."""
    doc = await get_document(db, document_id, user_id)
    if doc is None:
        return False
    await db.delete(doc)
    await db.commit()
    return True


async def get_parse_progress(document_id: str) -> dict:
    """Read parse progress from Redis for SSE streaming."""
    key = f"{REDIS_PROGRESS_PREFIX}{document_id}"
    data = await redis_client.get(key)
    if data is None:
        return {"status": "unknown", "current_page": 0, "total_pages": 0}
    return json.loads(data)


async def set_parse_progress(document_id: str, progress: dict) -> None:
    """Write parse progress to Redis."""
    key = f"{REDIS_PROGRESS_PREFIX}{document_id}"
    await redis_client.setex(key, REDIS_PROGRESS_TTL, json.dumps(progress))
