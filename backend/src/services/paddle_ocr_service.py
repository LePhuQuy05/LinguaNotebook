"""PaddleOCR-VL cloud API adapter — PDF → per-page markdown.

Job-based Baidu AI Studio API (https://ai.baidu.com/ai-doc/AISTUDIO/7mfz6dgx9):
submit PDF → poll job state → download JSONL results. Each
`layoutParsingResult` is one PDF page (lines can pack several); its
`markdown.text` becomes a `--- Page N ---` chunk — the same marker contract
`split_pages` / `markdown_to_block_records` consume, so the rest of the
parse pipeline is backend-agnostic.

Selected via the `OCR_BACKEND` setting ("paddle", or "auto" with a token
configured). Replaces the local HPD GPU path when the GPU is too slow.

Limitations: image files referenced by the result markdown (`markdown.images`)
are not downloaded — text-only blocks; RAG chunks come from text anyway.
"""

import json
import logging
import os
import tempfile
import time
from collections.abc import Callable

import fitz  # PyMuPDF
import httpx

from src.core.config import settings
from src.utils.hpd_parser import ProgressInfo

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 5
UPLOAD_TIMEOUT_SEC = 300  # large scanned PDFs can take a while to upload
POLL_TIMEOUT_SEC = 30


class PaddleOcrError(RuntimeError):
    """API-level failure: auth, network, job submit/query."""


def _slice_pdf(pdf_path: str, page_start: int, page_end: int | None) -> str:
    """Render the requested page range into a new temp PDF.

    The cloud API always processes the whole document; slicing locally keeps
    the worker's page_start/page_end contract intact.
    """
    doc = fitz.open(pdf_path)
    total = doc.page_count
    start = max(1, page_start) - 1
    end = min(page_end or total, total)
    sliced = fitz.open()
    sliced.insert_pdf(doc, from_page=start, to_page=end - 1)
    doc.close()
    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    sliced.save(tmp)
    sliced.close()
    return tmp


class PaddleOcrService:
    """Submit a PDF to PaddleOCR-VL and collect per-page markdown."""

    def __init__(
        self,
        token: str | None = None,
        job_url: str | None = None,
        model: str | None = None,
    ):
        self.token = token if token is not None else settings.paddle_ocr_token
        self.job_url = job_url if job_url is not None else settings.paddle_ocr_job_url
        self.model = model if model is not None else settings.paddle_ocr_model

    def _headers(self) -> dict:
        return {"Authorization": f"bearer {self.token}"}

    def _submit(self, pdf_path: str) -> str:
        """Upload the PDF and return the job id."""
        optional_payload = {
            "useDocOrientationClassify": False,
            "useDocUnwarping": False,
            "useChartRecognition": False,
        }
        data = {"model": self.model, "optionalPayload": json.dumps(optional_payload)}
        with open(pdf_path, "rb") as f:
            with httpx.Client(timeout=UPLOAD_TIMEOUT_SEC) as client:
                resp = client.post(
                    self.job_url,
                    headers=self._headers(),
                    data=data,
                    files={"file": ("document.pdf", f, "application/pdf")},
                )
        if resp.status_code != 200:
            raise PaddleOcrError(f"job submit failed ({resp.status_code}): {resp.text[:500]}")
        try:
            return resp.json()["data"]["jobId"]
        except (KeyError, ValueError) as exc:
            raise PaddleOcrError(f"unexpected submit response: {resp.text[:300]}") from exc

    def _query(self, job_id: str) -> dict:
        with httpx.Client(timeout=POLL_TIMEOUT_SEC) as client:
            resp = client.get(f"{self.job_url}/{job_id}", headers=self._headers())
        if resp.status_code != 200:
            raise PaddleOcrError(f"job query failed ({resp.status_code}): {resp.text[:500]}")
        try:
            return resp.json()["data"]
        except (KeyError, ValueError) as exc:
            raise PaddleOcrError(f"unexpected query response: {resp.text[:300]}") from exc

    def _download_jsonl(self, jsonl_url: str) -> str:
        with httpx.Client(timeout=POLL_TIMEOUT_SEC) as client:
            resp = client.get(jsonl_url)
        resp.raise_for_status()
        return resp.text

    def _results_from_jsonl(
        self, jsonl_url: str, done_data: dict, errors: list, page_offset: int = 0
    ) -> str:
        """Download the JSONL and build `--- Page N ---` markdown.

        One `layoutParsingResult` = one PDF page — the API packs several
        pages into each JSONL line (measured 2026-08-11: 47 lines carried
        186 results for a 186-page book), and `extractProgress.totalPages`
        counts results. `page_offset` realigns markers when the PDF was
        sliced for a page range (cloud API numbers results from 1).
        """
        text = self._download_jsonl(jsonl_url)
        lines = [ln for ln in text.strip().split("\n") if ln.strip()]
        total = done_data.get("extractProgress", {}).get("totalPages", len(lines))

        parts: list[str] = []
        parsed_pages = 0
        for line_num, line in enumerate(lines, start=1):
            try:
                result = json.loads(line)["result"]
                layouts = result.get("layoutParsingResults", [])
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                errors.append((parsed_pages + 1, f"malformed JSONL line {line_num}: {exc}"))
                continue
            for layout in layouts:
                parsed_pages += 1
                page_md = layout.get("markdown", {}).get("text", "").strip()
                parts.append(f"\n--- Page {page_offset + parsed_pages} ---\n")
                parts.append(page_md)
                parts.append("")

        if parsed_pages < total:
            errors.append(
                (page_offset + parsed_pages + 1, f"OCR returned {parsed_pages}/{total} pages")
            )
        logger.info(f"PaddleOCR: {parsed_pages} pages of markdown from {total}")
        return "".join(parts)

    def parse_pdf(
        self,
        pdf_path: str,
        page_start: int = 1,
        page_end: int | None = None,
        dpi: int = 100,  # interface parity with HPDFParser; cloud OCR ignores it
        max_tokens: int = 2048,  # interface parity with HPDFParser; cloud OCR ignores it
        progress_callback: Callable[[ProgressInfo], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> tuple[str, list[tuple[int, str]]]:
        """Submit → poll → download. Returns (combined_markdown, errors)."""
        if not self.token:
            raise PaddleOcrError(
                "PADDLE_OCR_TOKEN not configured — set it in .env or use OCR_BACKEND=local"
            )

        marker_offset = 0
        if page_start > 1 or page_end is not None:
            marker_offset = page_start - 1
            pdf_path = _slice_pdf(pdf_path, page_start, page_end)

        job_id = self._submit(pdf_path)
        logger.info(f"PaddleOCR job {job_id} submitted for {pdf_path}")

        errors: list[tuple[int, str]] = []
        t_start = time.time()
        while True:
            if cancel_check and cancel_check():
                logger.info("PaddleOCR job poll cancelled by user")
                errors.append((0, "Parse cancelled by user"))
                break

            data = self._query(job_id)
            state = data.get("state")
            if state == "pending":
                pass
            elif state == "running":
                progress = data.get("extractProgress", {})
                if progress_callback:
                    progress_callback(
                        ProgressInfo(
                            status="running",
                            current_page=progress.get("extractedPages", 0),
                            total_pages=progress.get("totalPages", 0),
                            elapsed_sec=time.time() - t_start,
                            eta_sec=0.0,
                            pages_per_sec=0.0,
                            errors=list(errors),
                        )
                    )
            elif state == "done":
                try:
                    jsonl_url = data["resultUrl"]["jsonUrl"]
                except KeyError as exc:
                    raise PaddleOcrError(f"done job missing resultUrl: {exc}") from exc
                markdown = self._results_from_jsonl(jsonl_url, data, errors, marker_offset)
                return markdown, errors
            elif state == "failed":
                msg = data.get("errorMsg", "unknown error")
                logger.error(f"PaddleOCR job {job_id} failed: {msg}")
                errors.append((0, f"PaddleOCR job failed: {msg}"))
                return "", errors
            else:
                raise PaddleOcrError(f"unexpected job state: {state!r}")

            time.sleep(POLL_INTERVAL_SEC)

        return "", errors
