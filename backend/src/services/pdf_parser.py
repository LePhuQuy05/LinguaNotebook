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
    mode: str = "fast",
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[str, list[tuple[int, str]], str]:
    """Parse a PDF using the best available method.

    Modes:
      - "fast": text extraction (PyMuPDF) for text PDFs, Marker fast for scans
      - "balanced": Marker OCR with surya VLM for best quality
      - "hpd": HPD OCR (GPU required, Intel XPU/CUDA)
      - "hybrid": HPD for all pages + Qwen2.5-VL re-parse of important pages
                 (TOC, tables, first pages) for high Japanese quality

    Returns (markdown_text, errors, method_used).
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

    # Image-based PDF — use selected OCR method
    if mode == "balanced":
        # Try Marker with surya VLM first
        from src.services.marker_parser import MarkerParser, has_marker_support
        if has_marker_support():
            logger.info("Using Marker OCR (balanced mode)")
            parser = MarkerParser(mode="balanced")
            try:
                markdown, errors, method = parser.convert_pdf(
                    pdf_path, page_start, page_end,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                )
                return markdown, errors, method
            except Exception as e:
                logger.warning(f"Marker failed, falling back to HPD: {e}")

    if mode == "fast":
        # Fast mode: try Marker text extraction first
        from src.services.marker_parser import MarkerParser, has_marker_support
        if has_marker_support():
            logger.info("Using Marker text extraction (fast mode)")
            parser = MarkerParser(mode="fast")
            try:
                markdown, errors, method = parser.convert_pdf(
                    pdf_path, page_start, page_end,
                    progress_callback=progress_callback,
                    cancel_check=cancel_check,
                )
                return markdown, errors, method
            except Exception as e:
                logger.warning(f"Marker fast failed, falling back to HPD: {e}")

    # HYBRID mode: HPD for all pages + Qwen2.5-VL re-parse of important pages
    if mode == "hybrid":
        return _parse_hybrid_hpd_qwen(
            pdf_path, page_start, page_end, dpi, max_tokens,
            progress_callback, cancel_check,
        )

    # Fall back to HPD OCR
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


def _parse_hybrid_hpd_qwen(
    pdf_path: str,
    page_start: int = 1,
    page_end: Optional[int] = None,
    dpi: int = 100,
    max_tokens: int = 2048,
    progress_callback: Optional[Callable] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
    max_qwen_pages: int = 15,
) -> tuple[str, list[tuple[int, str]], str]:
    """Hybrid: HPD parses all pages, Qwen2.5-VL re-parses important pages.

    Important pages (TOC, tables, first pages) get high-quality OCR.
    The rest uses fast HPD. Total time: HPD speed + N × ~200s.
    """
    import re

    from src.utils.hpd_parser import HPDFParser

    logger.info("Hybrid mode: HPD for all pages + Qwen for important pages")

    # Step 1: HPD parses everything
    parser = HPDFParser()
    parser.load_model()
    markdown, errors = parser.parse_pdf(
        pdf_path, page_start, page_end, dpi, max_tokens,
        progress_callback=progress_callback,
        cancel_check=cancel_check,
    )

    # Step 2: Find important pages from HPD output
    from src.services.qwen_vlm_parser import QwenVLCParser, is_important_page

    # Split markdown into per-page sections
    page_sections = re.split(r'(?=--- Page \d+ ---)', markdown)
    important_pages: list[int] = []
    for section in page_sections:
        m = re.match(r'--- Page (\d+) ---', section)
        if m:
            page_num = int(m.group(1))
            if is_important_page(section, page_num):
                important_pages.append(page_num)

    # Cap the number of Qwen pages
    important_pages = important_pages[:max_qwen_pages]

    if not important_pages:
        logger.info("No important pages detected — HPD output used as-is")
        return markdown, errors, "hybrid_hpd_only"

    logger.info(f"Qwen re-parsing {len(important_pages)} important pages: {important_pages}")

    # Step 3: Qwen re-parses important pages
    qwen = QwenVLCParser()
    replacements: dict[int, str] = {}
    for i, page_num in enumerate(important_pages):
        if cancel_check and cancel_check():
            break
        try:
            md = qwen.parse_page(pdf_path, page_num, dpi=100)
            replacements[page_num] = md
            logger.info(f"Qwen re-parsed page {page_num} ({i+1}/{len(important_pages)})")
        except Exception as e:
            errors.append((page_num, f"Qwen failed, kept HPD: {e}"))
            logger.error(f"Qwen page {page_num} failed: {e}")

    # Step 4: Replace important pages in combined markdown
    if replacements:
        new_sections = []
        for section in page_sections:
            m = re.match(r'--- Page (\d+) ---', section)
            if m and int(m.group(1)) in replacements:
                page_num = int(m.group(1))
                new_sections.append(f"--- Page {page_num} ---\n{replacements[page_num]}\n")
            else:
                new_sections.append(section)
        markdown = "".join(new_sections)

    return markdown, errors, "hybrid_hpd_qwen"
