"""Document API endpoints — upload, list, view, update, delete, parse progress SSE."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.core.security import decode_token
from src.services import parser_service as svc
from src.models.document import Document, DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    language: str | None = Query(None),
    dpi: int = Query(100, ge=72, le=200),
    page_start: int = Query(1, ge=1),
    page_end: int | None = Query(None, ge=1),
    mode: str = Query("fast"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF for parsing. Optional page range."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    file_data = await file.read()
    if len(file_data) > 524_288_000:
        raise HTTPException(400, "File exceeds 500MB maximum")

    document = await svc.create_document(
        db=db, user_id=user_id, filename=file.filename,
        file_data=file_data, mime_type=file.content_type or "application/pdf",
        language=language, dpi=dpi,
        page_start=page_start, page_end=page_end,
        parse_mode=mode,
    )
    return {"document_id": document.id, "status": document.status.value, "total_pages": document.total_pages, "page_range": f"{page_start}-{page_end or 'end'}"}


@router.get("")
async def list_documents(
    status: DocumentStatus | None = Query(None),
    language: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List user's documents."""
    result = await db.execute(
        select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc())
    )
    all_docs = result.scalars().all()

    if status:
        all_docs = [d for d in all_docs if d.status == status]
    if language:
        all_docs = [d for d in all_docs if d.language == language]

    total = len(all_docs)
    start = (page - 1) * per_page
    docs = all_docs[start:start + per_page]

    return {
        "items": [{"id": d.id, "filename": d.filename, "file_size_bytes": d.file_size_bytes,
                    "total_pages": d.total_pages, "language": d.language,
                    "status": d.status.value, "parse_method": d.parse_method,
                    "created_at": d.created_at.isoformat()} for d in docs],
        "total": total, "page": page,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str, user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get document with parsed blocks."""
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    blocks_result = await db.execute(
        select(Document).where(Document.id == document_id)  # ContentBlock imported below
    )
    from src.models.document import ContentBlock
    blocks_result = await db.execute(
        select(ContentBlock).where(ContentBlock.document_id == document_id).order_by(ContentBlock.page_number)
    )
    blocks = blocks_result.scalars().all()

    return {
        "id": doc.id, "filename": doc.filename, "file_size_bytes": doc.file_size_bytes,
        "total_pages": doc.total_pages, "language": doc.language,
        "status": doc.status.value, "parse_method": doc.parse_method,
        "error_message": doc.error_message,
        "created_at": doc.created_at.isoformat(),
        "blocks": [{"id": b.id, "page_number": b.page_number, "block_type": b.block_type.value,
                     "content_markdown": b.content_markdown, "bbox": b.bbox} for b in blocks],
    }


@router.patch("/{document_id}")
async def update_document(
    document_id: str, language: str | None = None,
    user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db),
):
    doc = await svc.update_document(db, document_id, user_id, language=language)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"id": doc.id, "language": doc.language}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str, user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    deleted = await svc.delete_document(db, document_id, user_id)
    if not deleted:
        raise HTTPException(404, "Document not found")
    return {"status": "deleted"}


@router.get("/{document_id}/parse/progress")
async def parse_progress(
    document_id: str, request: Request,
    token: str | None = Query(None),
):
    """SSE stream of real-time parsing progress.

    Supports auth via query param (?token=...) because browser EventSource
    cannot send custom headers.
    """
    # Authenticate via token query param or header
    user_id = None
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") == "access":
                user_id = payload["sub"]
        except Exception:
            pass

    if not user_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                payload = decode_token(auth_header[7:])
                user_id = payload["sub"]
            except Exception:
                pass

    if not user_id:
        # Return as SSE error event
        async def auth_error():
            yield f"data: {json.dumps({'status': 'error', 'message': 'Authentication required'})}\n\n"
        return StreamingResponse(auth_error(), media_type="text/event-stream")

    async def event_stream():
        last_page = -1
        while True:
            progress = await svc.get_parse_progress(document_id)
            current_page = progress.get("current_page", 0)

            if current_page != last_page or progress.get("status") != "running":
                yield f"data: {json.dumps(progress)}\n\n"
                last_page = current_page

            if progress.get("status") in ("completed", "completed_with_errors", "failed", "not_found"):
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{document_id}/parse/progress/poll")
async def parse_progress_poll(
    document_id: str,
    token: str | None = Query(None),
):
    """Polling endpoint — returns progress as JSON (works through proxies)."""
    # Auth via token query param
    if token:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                token = None
        except Exception:
            token = None

    progress = await svc.get_parse_progress(document_id)
    if not progress or not progress.get("status"):
        return {"status": "waiting", "current_page": 0, "total_pages": 0}

    return progress


@router.post("/{document_id}/parse/cancel")
async def cancel_parse(document_id: str):
    """Cancel a running parse job and update document status."""
    from src.core.redis import sync_redis_client as redis
    from src.core.database import AsyncSessionLocal
    from sqlalchemy import select, update
    from src.models.document import Document, DocumentStatus

    redis.setex(f"parse:cancel:{document_id}", 3600, "1")
    redis.setex(f"parse:progress:{document_id}", 3600, '{"status":"cancelled","current_page":0,"total_pages":0}')

    # Update document status in DB
    async with AsyncSessionLocal() as db:
        doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
        if doc:
            doc.status = DocumentStatus.failed
            doc.error_message = "Cancelled by user"
            await db.commit()

    return {"status": "cancelled", "document_id": document_id}
