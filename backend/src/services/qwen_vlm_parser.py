"""Qwen2.5-VL parser — high-quality OCR for important pages via llama-server.

Connects to llama-server (SYCL/GPU) exposing an OpenAI-compatible API.
Used in hybrid mode for pages where HPD quality is insufficient
(TOC pages, tables, dense kanji pages).
"""

import base64
import io
import json
import logging
import time
import urllib.request
from typing import Optional

import fitz
from PIL import Image

logger = logging.getLogger(__name__)


class QwenVLCParser:
    """OCR a single page using Qwen2.5-VL via OpenAI-compatible API."""

    def __init__(self, base_url: str = "http://127.0.0.1:18092/v1"):
        self.base_url = base_url
        self.timeout = 900  # 15 min per page max

    def ocr_page(self, pil_image: Image.Image, dpi_note: str = "") -> str:
        """OCR a PIL image. Returns markdown text."""
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        payload = {
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text",
                     "text": "Convert this document page to markdown. "
                             "Preserve the original Japanese text exactly. "
                             "Do not repeat content. "
                             "Output only the markdown content."},
                ],
            }],
            "max_tokens": 2048,
            "temperature": 0.1,
            "repeat_penalty": 1.3,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        resp = json.loads(urllib.request.urlopen(req, timeout=self.timeout).read())
        elapsed = time.time() - t0
        md = resp["choices"][0]["message"]["content"]

        # Strip markdown code fences if present
        md = md.strip()
        if md.startswith("```"):
            lines = md.split("\n")
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            md = "\n".join(lines).strip()

        logger.info(f"Qwen OCR page done in {elapsed:.0f}s, {len(md)} chars")
        return md

    def parse_page(self, pdf_path: str, page_num: int, dpi: int = 100) -> str:
        """OCR a specific page from a PDF. Returns markdown."""
        doc = fitz.open(pdf_path)
        idx = max(0, page_num - 1)
        if idx >= doc.page_count:
            doc.close()
            raise ValueError(f"Page {page_num} out of range")
        page = doc[idx]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        doc.close()
        return self.ocr_page(img)


def is_important_page(markdown_content: str, page_num: int) -> bool:
    """Heuristic: is this page important enough for high-quality OCR?

    Important = TOC pages, table-heavy pages, or early book pages
    (cover, preface) where HPD errors are most damaging.
    """
    # TOC pages (Japanese textbook patterns)
    toc_markers = ["目次", "もくじ", "Contents", "目 次"]
    for m in toc_markers:
        if m in markdown_content:
            return True

    # Table-heavy pages
    if markdown_content.count("<BLOCK>table") >= 3:
        return True

    # Early pages (cover, copyright, preface) — pages 1-6
    if page_num <= 6:
        return True

    # Pages with dense kanji lists (vocabulary index pages)
    if "課" in markdown_content and "索引" in markdown_content:
        return True

    return False
