"""PaddleOCR-VL cloud API adapter — PDF → per-page markdown.

Job-based Baidu AI Studio API (https://ai.baidu.com/ai-doc/AISTUDIO/7mfz6dgx9):
submit PDF → poll job state → download JSONL results. Each
`layoutParsingResult` is one PDF page (lines can pack several); its
`markdown.text` becomes a `--- Page N ---` chunk — the same marker contract
`split_pages` / `markdown_to_block_records` consume, so the rest of the
parse pipeline is backend-agnostic.

Large PDFs are split into ≤ CHUNK_TARGET_MB page-slice chunks and submitted
as one job each: the API ingests at ~1 MB/min and drops connections past
~17 min, so a single 16 MB job is a coin flip (measured 2026-08-11).

Selected via the `OCR_BACKEND` setting ("paddle", or "auto" with a token
configured). Replaces the local HPD GPU path when the GPU is too slow.

Limitations: image files referenced by the result markdown (`markdown.images`)
are not downloaded — text-only blocks; RAG chunks come from text anyway.
"""

import json
import logging
import math
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass

import fitz  # PyMuPDF
import httpx

from src.core.config import settings
from src.utils.hpd_parser import ProgressInfo

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 5
UPLOAD_TIMEOUT_SEC = 300  # large scanned PDFs can take a while to upload
POLL_TIMEOUT_SEC = 30
# The API ingests PDFs at roughly 1 MB/minute and drops the connection
# around the 17-18 minute mark (measured 2026-08-11: 2 of 3 uploads of a
# 16 MB book died with RemoteProtocolError). Keep each job small enough
# to finish well under that ceiling.
CHUNK_TARGET_MB = 4


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


def _page_count(pdf_path: str) -> int:
    doc = fitz.open(pdf_path)
    total = doc.page_count
    doc.close()
    return total


def _split_into_chunks(pdf_path: str) -> list[tuple[str, int, int]]:
    """Split a large PDF into ≤ CHUNK_TARGET_MB slices (temp files).

    Returns [(temp_path, first_page, last_page)] in page order with
    absolute page numbers; the original path alone when it fits in one
    chunk (no temp file created).
    """
    size = os.path.getsize(pdf_path)
    if size <= CHUNK_TARGET_MB * 1024 * 1024:
        return [(pdf_path, 1, _page_count(pdf_path))]

    total = _page_count(pdf_path)
    n_chunks = max(2, math.ceil(size / (CHUNK_TARGET_MB * 1024 * 1024)))
    pages_per = math.ceil(total / n_chunks)
    chunks: list[tuple[str, int, int]] = []
    for i in range(n_chunks):
        first = i * pages_per + 1
        last = min((i + 1) * pages_per, total)
        if first > total:
            break
        chunks.append((_slice_pdf(pdf_path, first, last), first, last))
    logger.info(
        f"PaddleOCR: splitting {size / 1e6:.1f} MB / {total} pages into "
        f"{len(chunks)} chunks of ≤{CHUNK_TARGET_MB} MB"
    )
    return chunks


@dataclass
class _ChunkJob:
    """One submitted job and its collected state."""

    first: int
    last: int
    job_id: str
    jsonl_url: str | None = None
    total_pages: int = 0
    extracted: int = 0
    failed: str | None = None


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
        """Submit → poll → download. Returns (combined_markdown, errors).

        PDFs larger than CHUNK_TARGET_MB are split into page-slice chunks
        and submitted as one job each — the API ingests at ~1 MB/min and
        drops connections past ~17 min, so one 16 MB job is a coin flip.
        Chunk markers keep absolute page numbers via per-chunk offsets.
        """
        if not self.token:
            raise PaddleOcrError(
                "PADDLE_OCR_TOKEN not configured — set it in .env or use OCR_BACKEND=local"
            )

        marker_offset = 0
        if page_start > 1 or page_end is not None:
            marker_offset = page_start - 1
            pdf_path = _slice_pdf(pdf_path, page_start, page_end)

        # The API ingests the file before creating the job — for large
        # scanned PDFs that takes minutes with zero job progress to show.
        # Emit a phase hint so the frontend can label the stall.
        if progress_callback:
            progress_callback(ProgressInfo(
                status="running", current_page=0, total_pages=0,
                elapsed_sec=0.0, eta_sec=0.0, pages_per_sec=0.0,
                errors=[], phase="uploading",
            ))

        chunks = _split_into_chunks(pdf_path)
        jobs: list[_ChunkJob] = []
        errors: list[tuple[int, str]] = []
        try:
            for chunk_path, first, last in chunks:
                job_id = self._submit(chunk_path)
                logger.info(
                    f"PaddleOCR job {job_id} submitted for {chunk_path} "
                    f"(pages {first}-{last})"
                )
                jobs.append(_ChunkJob(first=first, last=last, job_id=job_id))
        finally:
            # The server has the bytes once submit returns; don't leak temps.
            for chunk_path, _, _ in chunks:
                if chunk_path != pdf_path:
                    os.unlink(chunk_path)

        t_start = time.time()
        while True:
            if cancel_check and cancel_check():
                logger.info("PaddleOCR job poll cancelled by user")
                errors.append((0, "Parse cancelled by user"))
                break

            all_terminal = True
            for job in jobs:
                if job.jsonl_url or job.failed:
                    continue
                data = self._query(job.job_id)
                state = data.get("state")
                if state == "done":
                    try:
                        job.jsonl_url = data["resultUrl"]["jsonUrl"]
                    except KeyError as exc:
                        raise PaddleOcrError(f"done job missing resultUrl: {exc}") from exc
                    job.total_pages = (
                        data.get("extractProgress", {}).get("totalPages", 0)
                    )
                elif state == "running":
                    job.extracted = (
                        data.get("extractProgress", {}).get("extractedPages", 0)
                    )
                    all_terminal = False
                elif state == "failed":
                    msg = data.get("errorMsg", "unknown error")
                    job.failed = msg
                    errors.append((
                        job.first,
                        f"chunk pages {job.first}-{job.last} failed: {msg}",
                    ))
                    logger.error(f"PaddleOCR job {job.job_id} failed: {msg}")
                elif state == "pending":
                    all_terminal = False
                else:
                    raise PaddleOcrError(f"unexpected job state: {state!r}")

            if all_terminal:
                break

            if progress_callback:
                progress_callback(
                    ProgressInfo(
                        status="running",
                        current_page=sum(j.extracted for j in jobs),
                        total_pages=sum(j.last - j.first + 1 for j in jobs),
                        elapsed_sec=time.time() - t_start,
                        eta_sec=0.0,
                        pages_per_sec=0.0,
                        errors=list(errors),
                        phase="extracting",
                    )
                )
            time.sleep(POLL_INTERVAL_SEC)

        # Assemble per-chunk markdown in page order.
        parts: list[str] = []
        for job in jobs:
            if job.failed or not job.jsonl_url:
                continue
            parts.append(self._results_from_jsonl(
                job.jsonl_url,
                {"extractProgress": {"totalPages": job.total_pages}},
                errors,
                page_offset=marker_offset + job.first - 1,
            ))
        return "".join(parts), errors
