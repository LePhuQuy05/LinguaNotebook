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


@celery_app.task(name="parse_pdf", bind=True, max_retries=3)
def parse_pdf_task(self, document_id: str, object_key: str, dpi: int = 100) -> dict:
    """Parse a PDF document page by page using HPD model.

    Saves combined markdown to storage and updates document status in DB.
    """
    from src.core.storage import get_storage_client
    import io

    parser = _get_parser()

    try:
        # Download PDF from storage to memory
        client = get_storage_client()
        response = client.get_object(Bucket=settings.storage_bucket, Key=object_key)
        pdf_bytes = response["Body"].read()

        # Write to temp file (PyMuPDF needs a file path)
        import tempfile
        import os
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

        # Signal completion
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(set_parse_progress(document_id, {
            "status": "completed_with_errors" if errors else "completed",
            "result_key": result_key,
            "total_pages": len(combined_markdown.split("--- Page")) - 1,
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
