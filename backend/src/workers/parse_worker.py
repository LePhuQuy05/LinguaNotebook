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
    """Lazy-load the HPD parser. Called at worker startup on first task."""
    global _parser
    if _parser is None:
        _parser = HPDFParser(
            model_dir=settings.hpd_model_path,
            use_gpu=settings.gpu_enabled,
        )
        _parser.load_model()
    return _parser


def _progress_callback(document_id: str, info: ProgressInfo) -> None:
    """Emit parsing progress to Redis for SSE streaming."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(set_parse_progress(document_id, {
            "status": info.status,
            "current_page": info.current_page,
            "total_pages": info.total_pages,
            "elapsed_sec": info.elapsed_sec,
            "eta_sec": info.eta_sec,
            "pages_per_sec": info.pages_per_sec,
            "errors": info.errors,
        }))
    finally:
        loop.close()


async def _save_content_blocks(document_id: str, markdown: str, errors: list):
    """Parse HPD markdown into ContentBlock records and save to DB."""
    import re
    from sqlalchemy import select, update
    from src.core.database import AsyncSessionLocal
    from src.models.document import Document, ContentBlock, BlockType, DocumentStatus

    async with AsyncSessionLocal() as db:
        # Get document to find user_id
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return
        user_id = doc.user_id

        # Parse markdown into blocks per page
        pages = re.split(r'--- Page \d+ ---', markdown)
        blocks_saved = 0

        for page_idx, page_content in enumerate(pages):
            if not page_content.strip():
                continue
            page_num = page_idx + 1

            # Split by <BLOCK> tags
            block_pattern = re.compile(
                r'<BLOCK>(header|paragraph|table|list|image_caption)\s*\[(\d+),(\d+),(\d+),(\d+)\](.*?)</BLOCK>',
                re.DOTALL,
            )
            matches = block_pattern.findall(page_content)

            if not matches:
                # No structured blocks — save whole page as one paragraph block
                block = ContentBlock(
                    document_id=document_id,
                    page_number=page_num,
                    block_type=BlockType.paragraph,
                    content_markdown=page_content.strip(),
                    bbox=None,
                    language=doc.language or "unknown",
                )
                db.add(block)
                blocks_saved += 1
                continue

            for match in matches:
                btype, x1, y1, x2, y2, content = match
                try:
                    block_type = BlockType(btype)
                except ValueError:
                    block_type = BlockType.paragraph

                block = ContentBlock(
                    document_id=document_id,
                    page_number=page_num,
                    block_type=block_type,
                    content_markdown=content.strip(),
                    bbox=[int(x1), int(y1), int(x2), int(y2)],
                    language=doc.language or "unknown",
                )
                db.add(block)
                blocks_saved += 1

        # Update document status
        doc.status = DocumentStatus.completed_with_errors if errors else DocumentStatus.completed
        doc.total_pages = pages[0].strip() and len(pages) or 0
        doc.parsed_content_path = f"parsed/{document_id}/combined.md"

        await db.commit()
        logger.info(f"Saved {blocks_saved} ContentBlocks for document {document_id}")


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

        # Parse markdown into ContentBlock records and save to DB
        total_pages = len(combined_markdown.split("--- Page")) - 1
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(_save_content_blocks(document_id, combined_markdown, errors))
        loop.close()

        # Trigger embed worker for RAG indexing
        from src.workers.embed_worker import embed_document_task
        embed_document_task.delay(document_id, user_id)

        # Signal completion
        loop = asyncio.new_event_loop()
        loop.run_until_complete(set_parse_progress(document_id, {
            "status": "completed_with_errors" if errors else "completed",
            "result_key": result_key,
            "total_pages": total_pages,
            "errors": errors,
        }))
        loop.close()

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
