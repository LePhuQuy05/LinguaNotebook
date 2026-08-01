"""Celery worker for PDF parsing with hybrid parser.

Auto-detects PDF text layer: PyMuPDF for text-based PDFs, HPD OCR for scanned PDFs.
Emits progress to Redis for frontend polling.
"""

import logging

from src.core.config import settings
from src.core.storage import get_storage_client, upload_file
from src.services.parser_service import set_parse_progress
from src.utils.hpd_parser import HPDFParser
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# HPD model loaded once per worker lifetime (for scanned PDFs)
_parser: HPDFParser | None = None


def _get_parser() -> HPDFParser:
    """Lazy-load HPD parser. Called only for image-based PDFs."""
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


def _progress_callback(document_id: str, info) -> None:
    """Emit parsing progress to Redis for frontend polling (sync)."""
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


def _deduplicate_repeated_lines(markdown: str, threshold: int = 5) -> str:
    """Remove HPD degeneration: consecutive repeated lines."""
    lines = markdown.split('\n')
    cleaned = []
    prev_line = None
    repeat_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped and stripped == prev_line:
            repeat_count += 1
            if repeat_count <= threshold:
                cleaned.append(line)
            elif repeat_count == threshold + 1:
                cleaned.append(f'[HPD repetition detected — {threshold}+ duplicates removed]')
        else:
            repeat_count = 0
            prev_line = stripped
            cleaned.append(line)

    return '\n'.join(cleaned)


def _save_content_blocks(document_id: str, markdown: str, errors: list, method: str = ""):
    """Parse markdown into ContentBlock records and save to DB."""
    import asyncio

    from sqlalchemy import select

    from src.core.database import AsyncSessionLocal
    from src.models.document import BlockType, ContentBlock, Document, DocumentStatus
    from src.models.knowledge_segment import KnowledgeSegment  # noqa: F401
    from src.models.learning import Lesson, LessonItem  # noqa: F401
    from src.models.schedule import Schedule  # noqa: F401
    from src.models.srs import SRSCard  # noqa: F401
    from src.models.sync import Device, ProgressSnapshot, SyncLog  # noqa: F401
    from src.models.user import User  # noqa: F401
    from src.services.hpd_markdown import markdown_to_block_records, split_pages

    # Detect and remove HPD degeneration
    markdown = _deduplicate_repeated_lines(markdown)

    async def _run():
        async with AsyncSessionLocal() as db:
            doc = (
                await db.execute(select(Document).where(Document.id == document_id))
            ).scalar_one_or_none()
            if not doc:
                return

            # Typed blocks with page numbers taken from the `--- Page N ---`
            # markers — never from array indexes (the old split discarded the
            # numbers, shifting every page up by one).
            pages = split_pages(markdown)
            records = markdown_to_block_records(markdown)
            blocks_saved = 0

            for page_num, block in records:
                try:
                    btype = BlockType(block.block_type)
                except ValueError:
                    btype = BlockType.paragraph
                db.add(ContentBlock(
                    document_id=document_id, page_number=page_num,
                    block_type=btype, content_markdown=block.content,
                    bbox=None, language=doc.language or "unknown",
                ))
                blocks_saved += 1

            doc.status = (
                DocumentStatus.completed_with_errors if errors else DocumentStatus.completed
            )
            # Highest parsed page number — counts blank trailing pages too
            # (a page marker with zero blocks still exists as a page).
            doc.total_pages = max((n for n, _ in pages), default=0)
            doc.parse_method = method
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
                    page_start: int = 1, page_end: int = None,
                    mode: str = "fast") -> dict:
    """Parse a PDF using the best available method: text extraction or OCR."""
    try:
        # Download PDF from storage
        client = get_storage_client()
        response = client.get_object(Bucket=settings.storage_bucket, Key=object_key)
        pdf_bytes = response["Body"].read()

        # Write to temp file
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Get page count for progress
        import fitz
        pdf_doc = fitz.open(tmp_path)
        total_pages = pdf_doc.page_count
        start = max(1, page_start) - 1
        end = min(page_end or total_pages, total_pages)
        to_process = end - start
        pdf_doc.close()

        # Write INITIAL progress
        import json

        from src.core.redis import sync_redis_client
        sync_redis_client.setex(
            f"parse:progress:{document_id}", 3600,
            json.dumps({
                "status": "running", "current_page": 0,
                "total_pages": to_process, "elapsed_sec": 0,
                "eta_sec": 0, "pages_per_sec": 0, "errors": [],
            }),
        )

        # HYBRID: auto-detect and use best parser
        from src.services.pdf_parser import parse_pdf_hybrid
        combined_markdown, errors, method = parse_pdf_hybrid(
            pdf_path=tmp_path,
            page_start=page_start, page_end=page_end,
            dpi=dpi, mode=mode,
            progress_callback=lambda info: _progress_callback(document_id, info),
            cancel_check=lambda: _is_cancelled(document_id),
        )
        logger.info(f"Document {document_id} parsed via {method}: {len(combined_markdown)} chars")

        # Clean up temp file
        os.unlink(tmp_path)

        # Upload combined markdown to storage
        result_key = f"parsed/{document_id}/combined.md"
        upload_file(combined_markdown.encode("utf-8"), result_key, "text/markdown")

        # Calculate page count
        total_pages = len(combined_markdown.split("--- Page")) - 1

        # Signal completion via Redis FIRST (before slow DB operations)
        sync_redis_client.setex(
            f"parse:progress:{document_id}", 3600,
            json.dumps({
                "status": "completed_with_errors" if errors else "completed",
                "result_key": result_key,
                "total_pages": total_pages,
                "errors": errors,
            }, default=str),
        )

        # Save ContentBlocks to DB (can be slow, frontend already shows completed)
        try:
            _save_content_blocks(document_id, combined_markdown, errors, method)
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

        logger.info(f"Document {document_id} parse complete")
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
