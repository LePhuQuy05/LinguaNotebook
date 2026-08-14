"""Celery worker for PDF parsing.

Auto-detects PDF text layer: PyMuPDF for text-based PDFs, HPD OCR for scanned PDFs.
Emits progress to Redis for frontend polling. On success, hands off to the
embed worker so blocks become searchable in Qdrant.
"""

import logging

from src.core.config import settings
from src.core.storage import get_storage_client, upload_file
from src.services.parser_service import set_parse_progress
from src.utils.worker_loop import get_event_loop as _get_event_loop
from src.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _dispatch_embed(document_id: str) -> None:
    """Hand the parsed document to the embed worker (chunk → Qdrant)."""
    from src.workers.embed_worker import embed_document_task

    embed_document_task.delay(document_id=document_id, user_id=None)


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
            json.dumps(
                {
                    "status": info.status,
                    "current_page": info.current_page,
                    "total_pages": info.total_pages,
                    "elapsed_sec": info.elapsed_sec,
                    "eta_sec": info.eta_sec,
                    "pages_per_sec": info.pages_per_sec,
                    "errors": info.errors,
                    "phase": info.phase or "",
                },
                default=str,
            ),
        )
    except Exception as e:
        logger.error(f"Failed to write progress to Redis: {e}")


def _deduplicate_repeated_lines(markdown: str, threshold: int = 5) -> str:
    """Remove HPD degeneration: consecutive repeated lines."""
    lines = markdown.split("\n")
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
                cleaned.append(f"[HPD repetition detected — {threshold}+ duplicates removed]")
        else:
            repeat_count = 0
            prev_line = stripped
            cleaned.append(line)

    return "\n".join(cleaned)


def _save_content_blocks(document_id: str, markdown: str, errors: list, method: str = ""):
    """Parse markdown into ContentBlock records and save to DB."""
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
        from sqlalchemy import delete

        async with AsyncSessionLocal() as db:
            doc = (
                await db.execute(select(Document).where(Document.id == document_id))
            ).scalar_one_or_none()
            if not doc:
                return

            # A re-parse replaces the document's blocks — delete the old
            # ones first, in the same transaction, so a crash mid-save
            # rolls back and leaves the existing blocks intact.
            await db.execute(delete(ContentBlock).where(ContentBlock.document_id == document_id))

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
                db.add(
                    ContentBlock(
                        document_id=document_id,
                        page_number=page_num,
                        block_type=btype,
                        content_markdown=block.content,
                        bbox=None,
                        language=doc.language or "unknown",
                    )
                )
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

    # Run on the worker's persistent loop — never close it, or pooled
    # asyncpg connections die with the loop (see _get_event_loop).
    _get_event_loop().run_until_complete(_run())


def _save_curriculum_structure(document_id: str, markdown: str) -> None:
    """Extract the TOC-based curriculum map and persist DocumentStructure rows.

    Conservative by design: unknown structure → empty map, nothing written.
    Idempotent per document: existing rows are replaced on re-parse.
    """
    from sqlalchemy import delete

    from src.core.database import AsyncSessionLocal
    from src.models.document_structure import DocumentStructure
    from src.services.curriculum_service import extract_curriculum

    async def _run():
        rows = extract_curriculum(markdown)
        if not rows:
            return
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(DocumentStructure).where(DocumentStructure.document_id == document_id)
            )
            for i, row in enumerate(rows):
                db.add(
                    DocumentStructure(
                        document_id=document_id,
                        part=row["part"],
                        chapter_num=row["chapter_num"],
                        chapter_title=row["chapter_title"],
                        page_start=row["page_start"],
                        page_end=row["page_end"],
                        order=i,
                    )
                )
            await db.commit()
        logger.info(f"Saved {len(rows)} curriculum rows for document {document_id}")

    _get_event_loop().run_until_complete(_run())


@celery_app.task(name="parse_pdf", bind=True, max_retries=3)
def parse_pdf_task(
    self,
    document_id: str,
    object_key: str,
    dpi: int = 100,
    page_start: int = 1,
    page_end: int = None,
    mode: str = "fast",
) -> dict:
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
            f"parse:progress:{document_id}",
            3600,
            json.dumps(
                {
                    "status": "running",
                    "current_page": 0,
                    "total_pages": to_process,
                    "elapsed_sec": 0,
                    "eta_sec": 0,
                    "pages_per_sec": 0,
                    "errors": [],
                }
            ),
        )

        # Auto-detect: text layer → PyMuPDF, else HPD OCR
        from src.services.pdf_parser import parse_pdf_hybrid

        combined_markdown, errors, method = parse_pdf_hybrid(
            pdf_path=tmp_path,
            page_start=page_start,
            page_end=page_end,
            dpi=dpi,
            mode=mode,
            progress_callback=lambda info: _progress_callback(document_id, info),
            cancel_check=lambda: _is_cancelled(document_id),
        )
        # Strip HTML tags the OCR occasionally emits (<img>/<div> — dead
        # refs to images we never download). Clean once so both the MinIO
        # combined.md and the Postgres blocks stay clean at the source.
        from src.services.hpd_markdown import clean_markdown

        combined_markdown = clean_markdown(combined_markdown)
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
            f"parse:progress:{document_id}",
            3600,
            json.dumps(
                {
                    "status": "completed_with_errors" if errors else "completed",
                    "result_key": result_key,
                    "total_pages": total_pages,
                    "errors": errors,
                },
                default=str,
            ),
        )

        # Save ContentBlocks to DB (can be slow, frontend already shows completed)
        try:
            _save_content_blocks(document_id, combined_markdown, errors, method)
        except Exception as save_err:
            logger.error(f"Failed to save content blocks for {document_id}: {save_err}")
            sync_redis_client.setex(
                f"parse:progress:{document_id}",
                3600,
                json.dumps(
                    {
                        "status": "completed_with_errors",
                        "result_key": result_key,
                        "total_pages": total_pages,
                        "errors": errors + [f"DB save failed: {save_err}"],
                    },
                    default=str,
                ),
            )
            return {"status": "completed", "document_id": document_id, "errors": len(errors)}

        # Curriculum map from the book's TOC. Best effort: no map → empty,
        # never a parse failure.
        try:
            _save_curriculum_structure(document_id, combined_markdown)
        except Exception as struct_err:
            logger.error(f"Failed to save curriculum structure for {document_id}: {struct_err}")

        # Chunk + embed + index into Qdrant. Best effort: an embed failure
        # must not fail the parse — the doc is already saved and viewable.
        try:
            _dispatch_embed(document_id)
        except Exception as embed_err:
            logger.error(f"Failed to dispatch embed for {document_id}: {embed_err}")

        logger.info(f"Document {document_id} parse complete")
        return {"status": "completed", "document_id": document_id, "errors": len(errors)}

    except Exception as exc:
        logger.error(f"Parse failed for document {document_id}: {exc}")
        _get_event_loop().run_until_complete(
            set_parse_progress(
                document_id,
                {
                    "status": "failed",
                    "error": str(exc),
                },
            )
        )
        raise self.retry(exc=exc, countdown=60)
