"""Single-route PDF parser — auto-detects text layer.

For PDFs with embedded text: PyMuPDF extraction (instant, 100% accurate)
For scanned/image-based PDFs: OCR — PaddleOCR-VL cloud API or local HPD,
selected by the OCR_BACKEND setting (see src.core.config).

The Marker and hybrid (HPD + Qwen-VL re-parse) branches were removed:
the 2026-08-01 parse proved hybrid was a silent no-op that doubled parse
time with zero quality gain (spec 006). The Qwen-VL integration module
stays in the repo, unwired, for Stage 2 reuse.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content extracted from a single page."""

    page_num: int
    text: str
    blocks: list[dict] = field(default_factory=list)
    source: str = ""  # "text_layer" or "ocr"


def _has_text_layer(pdf_path: str, sample_pages: int = 3) -> bool:
    """Check if a PDF has embedded text by sampling a few pages.

    Returns True if any sampled page has >50 chars of real text
    (not just header/footer noise).
    """
    try:
        doc = fitz.open(pdf_path)
        total = doc.page_count
        # Sample pages spread across the document
        indices = [0, total // 3, total * 2 // 3]
        indices = [i for i in indices if i < total]

        text_chars = 0
        for idx in indices[:sample_pages]:
            page = doc[idx]
            text = page.get_text("text")
            text_chars += len(text.strip())

        doc.close()
        avg_chars = text_chars / max(len(indices), 1)
        has_text = avg_chars > 100  # Real content, not just footers
        logger.info(
            f"PDF text layer check: avg {avg_chars:.0f} chars/page → "
            f"{'text-based' if has_text else 'image-based'}"
        )
        return has_text

    except Exception as e:
        logger.warning(f"Failed to check PDF text layer: {e}")
        return False


def extract_text_pymupdf(
    pdf_path: str,
    page_start: int = 1,
    page_end: int | None = None,
    progress_callback: Callable | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[str, list[tuple[int, str]]]:
    """Extract text from a PDF using PyMuPDF's built-in text extraction.

    For PDFs with embedded text layers. Extremely fast (0.01-0.05s/page)
    and 100% accurate since it reads the original text, not OCR.
    """
    import time

    doc = fitz.open(pdf_path)
    total = doc.page_count
    start = max(1, page_start) - 1
    end = min(page_end or total, total)
    to_process = end - start

    results: list[str] = []
    errors: list[tuple[int, str]] = []
    t_start = time.time()

    for idx in range(start, end):
        if cancel_check and cancel_check():
            logger.info("Text extraction cancelled by user")
            break

        page_num = idx + 1
        try:
            page = doc[idx]
            text = page.get_text("text")
            results.append(f"\n--- Page {page_num} ---\n{text.strip()}")

        except Exception as exc:
            errors.append((page_num, str(exc)))
            logger.error(f"Page {page_num} text extraction failed: {exc}")

        if progress_callback:
            elapsed = time.time() - t_start
            done = len(results) + len(errors)
            pps = done / elapsed if elapsed > 0 else 0
            left = to_process - done

            progress_callback(
                type(
                    "Progress",
                    (),
                    {
                        "status": "running",
                        "current_page": done,
                        "total_pages": to_process,
                        "elapsed_sec": elapsed,
                        "eta_sec": (left / pps) if pps > 0 else 0,
                        "pages_per_sec": pps,
                        "errors": list(errors),
                    },
                )
            )

    doc.close()

    combined = "".join(results)
    if errors:
        combined += "\n--- Extraction Errors ---\n"
        for pn, msg in errors:
            combined += f"- Page {pn}: {msg}\n"

    return combined, errors


def _ocr_backend() -> str:
    """Which OCR engine to use for image-based PDFs."""
    from src.core.config import settings

    backend = settings.ocr_backend
    if backend == "auto":
        return "paddle" if settings.paddle_ocr_token else "local"
    return backend


def parse_pdf_hybrid(
    pdf_path: str,
    page_start: int = 1,
    page_end: int | None = None,
    dpi: int = 100,
    max_tokens: int = 2048,
    mode: str = "fast",
    progress_callback: Callable | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> tuple[str, list[tuple[int, str]], str]:
    """Parse a PDF: text layer → PyMuPDF, else the configured OCR backend.

    The `mode` parameter is accepted for backward compatibility with older
    API clients and queued Celery tasks, but is always ignored — the Marker
    and hybrid (Qwen-VL) branches were removed (2026-08-01 evidence: hybrid
    was a silent no-op doubling parse time).

    OCR backend is per OCR_BACKEND setting: "paddle" → PaddleOCR-VL cloud
    API (no local GPU needed), "local" → HPD on XPU/CUDA, "auto" → paddle
    when a token is configured, else local.

    Returns (markdown_text, errors, method_used) where method_used is
    "text_layer" or "ocr".
    """
    # Check if PDF has embedded text
    if _has_text_layer(pdf_path):
        logger.info("Using PyMuPDF text extraction (text-based PDF)")
        markdown, errors = extract_text_pymupdf(
            pdf_path,
            page_start,
            page_end,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        return markdown, errors, "text_layer"

    # Image-based PDF — configured OCR backend
    if _ocr_backend() == "paddle":
        from src.services.paddle_ocr_service import PaddleOcrService

        logger.info("Using PaddleOCR-VL cloud API (image-based PDF)")
        markdown, errors = PaddleOcrService().parse_pdf(
            pdf_path,
            page_start,
            page_end,
            dpi,
            max_tokens,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        return markdown, errors, "ocr"

    logger.info("Using HPD OCR (image-based PDF)")
    from src.core.config import settings as _settings
    from src.utils.hpd_parser import HPDFParser

    parser = HPDFParser(
        model_dir=_settings.hpd_model_path,
        use_gpu=_settings.gpu_enabled,
        gpu_type=getattr(_settings, "gpu_type", "cuda"),
    )
    parser.load_model()
    markdown, errors = parser.parse_pdf(
        pdf_path,
        page_start,
        page_end,
        dpi,
        max_tokens,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
    return markdown, errors, "ocr"
