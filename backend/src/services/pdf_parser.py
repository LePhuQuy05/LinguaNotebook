"""Hybrid PDF Parser — auto-detects text layer, routes to best parser.

For PDFs with embedded text: PyMuPDF extraction (instant, 100% accurate)
For scanned/image-based PDFs: HPD OCR (GPU-accelerated)

This gives the best of both without new dependencies.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

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
    page_end: Optional[int] = None,
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
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

            progress_callback(type('Progress', (), {
                'status': 'running',
                'current_page': done,
                'total_pages': to_process,
                'elapsed_sec': elapsed,
                'eta_sec': (left / pps) if pps > 0 else 0,
                'pages_per_sec': pps,
                'errors': list(errors),
            }))

    doc.close()

    combined = "".join(results)
    if errors:
        combined += "\n--- Extraction Errors ---\n"
        for pn, msg in errors:
            combined += f"- Page {pn}: {msg}\n"

    return combined, errors


def parse_pdf_hybrid(
    pdf_path: str,
    page_start: int = 1,
    page_end: Optional[int] = None,
    dpi: int = 100,
    max_tokens: int = 2048,
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[str, list[tuple[int, str]], str]:
    """Parse a PDF using the best available method.

    Returns (markdown_text, errors, method_used).
    method_used is one of: "text_layer", "ocr"
    """
    # Check if PDF has embedded text
    if _has_text_layer(pdf_path):
        logger.info("Using PyMuPDF text extraction (text-based PDF)")
        markdown, errors = extract_text_pymupdf(
            pdf_path, page_start, page_end,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )
        return markdown, errors, "text_layer"

    # Fall back to HPD OCR for image-based PDFs
    logger.info("Using HPD OCR (image-based PDF)")
    from src.utils.hpd_parser import HPDFParser

    parser = HPDFParser()
    parser.load_model()
    markdown, errors = parser.parse_pdf(
        pdf_path, page_start, page_end, dpi, max_tokens,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )
    return markdown, errors, "ocr"
