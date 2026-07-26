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
    """Parse HPD markdown into ContentBlock records and save to DB (sync)."""
    import re
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from src.core.config import settings
    from src.models.document import Document, ContentBlock, BlockType, DocumentStatus

    # Use sync engine for Celery tasks
    sync_url = settings.database_url.replace("+asyncpg", "").replace("postgresql+asyncpg", "postgresql")
    engine = create_engine(sync_url)

    with Session(engine) as db:
        doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
        if not doc:
            engine.dispose()
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
                block = ContentBlock(
                    document_id=document_id, page_number=page_num,
                    block_type=BlockType.paragraph,
                    content_markdown=page_content.strip(),
                    bbox=None, language=doc.language or "unknown",
                )
                db.add(block)
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
        doc.total_pages = pages[0].strip() and len(pages) or 0
        doc.parsed_content_path = f"parsed/{document_id}/combined.md"
        db.commit()
        logger.info(f"Saved {blocks_saved} ContentBlocks for document {document_id}")
        engine.dispose()


@celery_app.task(name="parse_pdf", bind=True, max_retries=3)
def parse_pdf_task(self, document_id: str, object_key: str, dpi: int = 100) -> dict:
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

        # Parse the PDF
        combined_markdown, errors = parser.parse_pdf(
            pdf_path=tmp_path,
            dpi=dpi,
            progress_callback=lambda info: _progress_callback(document_id, info),
        )

        # Clean up temp file
        os.unlink(tmp_path)

        # Upload combined markdown to storage
        result_key = f"parsed/{document_id}/combined.md"
        upload_file(combined_markdown.encode("utf-8"), result_key, "text/markdown")

        # Parse markdown into ContentBlock records and save to DB (sync)
        total_pages = len(combined_markdown.split("--- Page")) - 1
        _save_content_blocks(document_id, combined_markdown, errors)

        # Signal completion via sync Redis
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
