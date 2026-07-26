"""Document API endpoints — upload, list, view, update, delete, parse progress SSE."""

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.dependencies import get_current_user_id
from src.services import parser_service as svc
from src.models.document import DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    language: str | None = Query(None),
    dpi: int = Query(100, ge=72, le=200),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF for parsing."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    file_data = await file.read()
    if len(file_data) > 524_288_000:  # 500MB
        raise HTTPException(400, "File exceeds 500MB maximum")

    document = await svc.create_document(
        db=db,
        user_id=user_id,
        filename=file.filename,
        file_data=file_data,
        mime_type=file.content_type or "application/pdf",
        language=language,
        dpi=dpi,
    )

    return {
        "document_id": document.id,
        "status": document.status.value,
        "total_pages": document.total_pages,
    }


@router.get("")
async def list_documents(
    status: DocumentStatus | None = Query(None),
    language: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List user's documents with optional filters."""
    documents, total = await svc.get_documents(
        db=db, user_id=user_id, status=status, language=language, page=page, per_page=per_page
    )
    return {
        "items": [
            {
                "id": d.id,
                "filename": d.filename,
                "file_size_bytes": d.file_size_bytes,
                "total_pages": d.total_pages,
                "language": d.language,
                "status": d.status.value,
                "created_at": d.created_at.isoformat(),
            }
            for d in documents
        ],
        "total": total,
        "page": page,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get document details with parsed content blocks."""
    document = await svc.get_document(db, document_id, user_id)
    if document is None:
        raise HTTPException(404, "Document not found")

    blocks = []
    for block in document.blocks:
        blocks.append({
            "id": block.id,
            "page_number": block.page_number,
            "block_type": block.block_type.value,
            "content_markdown": block.content_markdown,
            "bbox": block.bbox,
        })

    return {
        "id": document.id,
        "filename": document.filename,
        "file_size_bytes": document.file_size_bytes,
        "total_pages": document.total_pages,
        "language": document.language,
        "status": document.status.value,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat(),
        "blocks": blocks,
    }


@router.patch("/{document_id}")
async def update_document(
    document_id: str,
    language: str | None = None,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update document metadata."""
    doc = await svc.update_document(db, document_id, user_id, language=language)
    if doc is None:
        raise HTTPException(404, "Document not found")
    return {"id": doc.id, "language": doc.language}


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document. Returns 409 if SRS cards depend on it."""
    deleted = await svc.delete_document(db, document_id, user_id)
    if not deleted:
        raise HTTPException(404, "Document not found")
    return {"status": "deleted"}


@router.get("/{document_id}/parse/progress")
async def parse_progress(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """SSE stream of real-time parsing progress."""

    async def event_stream():
        last_page = -1
        while True:
            progress = await svc.get_parse_progress(document_id)
            current_page = progress.get("current_page", 0)

            if current_page != last_page or progress.get("status") != "running":
                yield f"data: {json.dumps(progress)}\n\n"
                last_page = current_page

            if progress.get("status") in (
                "completed", "completed_with_errors", "failed", "not_found"
            ):
                return

            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
