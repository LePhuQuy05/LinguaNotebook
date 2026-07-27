"""Celery worker for PDF parsing with HPD model.

Loads the model once at startup, processes pages sequentially,
and emits progress to Redis for SSE streaming.
"""

import logging

from src.core.config import settings
from src.core.storage import get_storage_client, upload_file
from src.workers.celery_app import celery_app
from src.services.parser_service import set_parse_progress
from src.utils.hpd_parser import HPDFParser, ProgressInfo

logger = logging.getLogger(__name__)

# Model loaded once per worker lifetime
_parser: HPDFParser | None = None


def _get_parser() -> HPDFParser:
    """Lazy-load HPD parser. Called at worker startup on first task."""
    global _parser
    if _parser is None:
        gpu_type = getattr(settings, 'gpu_type', 'cuda')
        _parser = HPDFParser(
            model_dir=settings.hpd_model_path,
            use_gpu=settings.gpu_enabled,
            gpu_type=gpu_type,
        )
        _parser.load_model()
    return _parser


def _is_cancelled(document_id: str) -> bool:
    """Check if a cancel flag has been set for this document."""
    from src.core.redis import sync_redis_client
    return sync_redis_client.exists(f"parse:cancel:{document_id}") > 0


def _progress_callback(document_id: str, info: ProgressInfo) -> None:
    """Emit parsing progress to Redis for SSE streaming (sync)."""
    import json
    from src.core.redis import sync_redis_client
    try:
        sync_redis_client.setex(
            f"parse:progress:{document_id}",
            3600,
            json.dumps({
                "status": info.status,
                "current_page": info.current_page,
                "total_pages": info.total_pages,
                "elapsed_sec": info.elapsed_sec,
                "eta_sec": info.eta_sec,
                "pages_per_sec": info.pages_per_sec,
                "errors": info.errors,
            }, default=str),
        )
    except Exception as e:
        logger.error(f"Failed to write progress to Redis: {e}")


def _save_content_blocks(document_id: str, markdown: str, errors: list):
    """Parse HPD markdown into ContentBlock records and save to DB."""
    import re
    import asyncio
    from sqlalchemy import select
    from src.core.database import AsyncSessionLocal, Base
    from src.core.config import settings
    from src.models.document import Document, ContentBlock, BlockType, DocumentStatus
    # Import all models so FK relationships resolve
    from src.models.user import User  # noqa: F401
    from src.models.knowledge_segment import KnowledgeSegment  # noqa: F401
    from src.models.learning import Lesson, LessonItem  # noqa: F401
    from src.models.schedule import Schedule  # noqa: F401
    from src.models.srs import SRSCard  # noqa: F401
    from src.models.sync import Device, SyncLog, ProgressSnapshot  # noqa: F401

    async def _run():
        async with AsyncSessionLocal() as db:
            doc = (await db.execute(select(Document).where(Document.id == document_id))).scalar_one_or_none()
            if not doc:
                return

            pages = re.split(r'--- Page \d+ ---', markdown)
            blocks_saved = 0

            for page_idx, page_content in enumerate(pages):
                if not page_content.strip():
                    continue
                page_num = page_idx + 1

                block_pattern = re.compile(
                    r'<BLOCK>(header|paragraph|table|list|image_caption)\s*\[(\d+),(\d+),(\d+),(\d+)\](.*?)</BLOCK>',
                    re.DOTALL,
                )
                matches = block_pattern.findall(page_content)

                if not matches:
                    db.add(ContentBlock(
                        document_id=document_id, page_number=page_num,
                        block_type=BlockType.paragraph,
                        content_markdown=page_content.strip(),
                        bbox=None, language=doc.language or "unknown",
                    ))
                    blocks_saved += 1
                    continue

                for btype, x1, y1, x2, y2, content in matches:
                    try:
                        block_type = BlockType(btype)
                    except ValueError:
                        block_type = BlockType.paragraph
                    db.add(ContentBlock(
                        document_id=document_id, page_number=page_num,
                        block_type=block_type, content_markdown=content.strip(),
                        bbox=[int(x1), int(y1), int(x2), int(y2)],
                        language=doc.language or "unknown",
                    ))
                    blocks_saved += 1

            doc.status = DocumentStatus.completed_with_errors if errors else DocumentStatus.completed
            # Count pages that have actual content (skip empty leading/trailing splits)
            doc.total_pages = sum(1 for p in pages if p.strip())
            doc.parsed_content_path = f"parsed/{document_id}/combined.md"
            await db.commit()
            logger.info(f"Saved {blocks_saved} ContentBlocks for document {document_id}")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(name="parse_pdf", bind=True, max_retries=3)
def parse_pdf_task(self, document_id: str, object_key: str, dpi: int = 100,
                    page_start: int = 1, page_end: int = None) -> dict:
    """Parse a PDF document page by page using HPD model.

    Saves combined markdown to storage and updates document status in DB.
    """
    parser = _get_parser()

    try:
        # Download PDF from storage to memory
        client = get_storage_client()
        response = client.get_object(Bucket=settings.storage_bucket, Key=object_key)
        pdf_bytes = response["Body"].read()

        # Write to temp file (PyMuPDF needs a file path)
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Get total page count for progress tracking
        import fitz
        pdf_doc = fitz.open(tmp_path)
        total_pages = pdf_doc.page_count
        start = max(1, page_start) - 1
        end = min(page_end or total_pages, total_pages)
        to_process = end - start
        pdf_doc.close()

        # Write INITIAL progress so frontend knows worker picked up the task
        from src.core.redis import sync_redis_client
        import json as _json
        sync_redis_client.setex(
            f"parse:progress:{document_id}", 3600,
            _json.dumps({
                "status": "running",
                "current_page": 0,
                "total_pages": to_process,
                "elapsed_sec": 0,
                "eta_sec": 0,
                "pages_per_sec": 0,
                "errors": [],
            }),
        )

        # Parse the PDF (with cancel check + page range)
        combined_markdown, errors = parser.parse_pdf(
            pdf_path=tmp_path,
            page_start=page_start,
            page_end=page_end,
            dpi=dpi,
            progress_callback=lambda info: _progress_callback(document_id, info),
            cancel_check=lambda: _is_cancelled(document_id),
        )

        # Clean up temp file
        os.unlink(tmp_path)

        # Upload combined markdown to storage
        result_key = f"parsed/{document_id}/combined.md"
        upload_file(combined_markdown.encode("utf-8"), result_key, "text/markdown")

        # Calculate page count from markdown
        total_pages = len(combined_markdown.split("--- Page")) - 1

        # Signal completion via sync Redis FIRST (before slow DB operations)
        import json
        from src.core.redis import sync_redis_client
        sync_redis_client.setex(
            f"parse:progress:{document_id}", 3600,
            json.dumps({
                "status": "completed_with_errors" if errors else "completed",
                "result_key": result_key,
                "total_pages": total_pages,
                "errors": errors,
            }, default=str),
        )

        # Parse markdown into ContentBlock records and save to DB
        # (can take a while on large documents — frontend already shows "completed")
        try:
            _save_content_blocks(document_id, combined_markdown, errors)
        except Exception as save_err:
            logger.error(f"Failed to save content blocks for {document_id}: {save_err}")
            sync_redis_client.setex(
                f"parse:progress:{document_id}", 3600,
                json.dumps({
                    "status": "completed_with_errors",
                    "result_key": result_key,
                    "total_pages": total_pages,
                    "errors": errors + [f"DB save failed: {save_err}"],
                }, default=str),
            )

        logger.info(f"Document {document_id} parsed successfully")
        return {"status": "completed", "document_id": document_id, "errors": len(errors)}

    except Exception as exc:
        logger.error(f"Parse failed for document {document_id}: {exc}")
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(set_parse_progress(document_id, {
            "status": "failed",
            "error": str(exc),
        }))
        loop.close()
        raise self.retry(exc=exc, countdown=60)
