# Spec: Migrate OCR from HPD to Marker

**Status**: ready-for-agent  
**Created**: 2026-07-28  
**Parent**: 001-lingua-notebook  
**Triage**: ready-for-agent

## Problem Statement

The current HPD-Parsing (PaddlePaddle) OCR pipeline has critical quality and performance issues that make it unsuitable for production use:

1. **15-20% character error rate for Japanese text** — the 1B-param InternViT + Qwen3-0.6B model was not designed for Japanese OCR. Characters are frequently corrupted (e.g., "仕事" → "什么事", "言葉" → "音業"), making RAG search unreliable and study content unusable.

2. **Speculative decoding causes text degeneration** — the Multi-Token Prediction (MTP) feature with `num_speculative_tokens=6` frequently gets stuck in infinite repetition loops. One page produced over 500 duplicate lines of the same sentence, bloating output and wasting parsing time. Multiple workarounds were attempted (repetition detection, disabling MTP, repetition penalty) but the root cause is architectural: HPD is an OCR model, not a document converter.

3. **No native table, TOC, or structure support** — HPD outputs raw markdown with `<BLOCK>` tags. Tables in Japanese textbooks are completely missed or garbled. A custom regex-based TOC parser was built as a workaround. The structured block output (`<BLOCK>header`, `<BLOCK>table`) is unreliable.

4. **Extremely slow on GPU** — 53 seconds per page on Intel Arc XPU (186-page textbook = 2.7 hours). This is impractical for any document larger than a few pages.

5. **Heavy model dependency** — 2.81GB model directory, Intel XPU-specific PyTorch setup, FlashAttention2 incompatibility, and platform-specific event loop bugs (Windows ProactorEventLoop conflicts with Celery async operations).

The user's primary use case — Japanese language textbooks — has **embedded text layers**. These PDFs don't need OCR at all; they need a document converter that reads the existing text, reconstructs structure, and outputs clean markdown.

## Solution

Replace HPD-Parsing with **[Marker](https://github.com/datalab-to/marker)** (Apache 2.0), a document-to-markdown converter that:

- **Reads embedded text first** — only invokes OCR (via surya VLM) when the text layer is garbled or missing. For modern textbooks, this means 0 character errors.
- **Runs 23.7 pages/second on CPU** in fast mode with `--disable_ocr` for PDFs with clean text layers. The same 186-page textbook converts in ~8 seconds instead of 2.7 hours.
- **Outputs structured markdown natively** — tables, headers, lists, equations, footnotes, and a built-in table of contents metadata block. No regex workarounds needed.
- **Supports CPU-only operation** via llama.cpp — eliminates the Intel Arc GPU dependency entirely.
- **Outputs multiple formats** — markdown, JSON (typed block tree with coordinates), HTML, and chunked RAG-ready output. The JSON output can directly replace the current `<BLOCK>` parsing.

### Architecture change

```
BEFORE (HPD):
  PDF → PyMuPDF render → PIL Image tiles → HPD 1B model OCR → Raw markdown
  → Regex <BLOCK> parse → ContentBlock DB records
  GPU: Intel Arc XPU, 2GB VRAM, 53s/page

AFTER (Marker):
  PDF → pdftext (embedded text) → Layout detection (rf-detr, CPU) 
  → Table reconstruction (CPU heuristics) → Structured markdown + JSON
  → JSON block tree → ContentBlock DB records
  GPU: None required (CPU fast mode, 0.04s/page)
```

## User Stories

1. As a language learner uploading a Japanese textbook PDF, I want the text to be extracted with near-100% accuracy, so that my flashcards and study materials contain correct Japanese characters.

2. As a language learner, I want tables in my textbook to be converted to readable markdown tables, so that I can study vocabulary lists and conjugation tables properly.

3. As a language learner, I want parsing to complete in seconds instead of hours, so that I can upload a document and start studying immediately.

4. As a self-hoster running LinguaNotebook on a laptop without a GPU, I want PDF parsing to work on CPU, so that I don't need special hardware.

5. As a developer maintaining LinguaNotebook, I want to remove the 2.81GB HPD model directory and Intel XPU dependencies, so that the project is lighter and easier to set up.

6. As a language learner, I want the table of contents to be extracted automatically, so that the study schedule generator can create a complete chapter-by-chapter plan without missing sections.

7. As a developer, I want the parse worker to run reliably without event loop crashes, so that users don't see "failed" status or stuck "Page 10 of 10" progress bars.

8. As a language learner uploading a scanned PDF (no text layer), I want OCR to still work as a fallback, so that old or image-based documents are still usable.

## Implementation Decisions

### 1. Marker runs on CPU in fast mode by default

**Decision**: Use Marker's fast mode (`--disable_ocr`) as the default. PDFs with embedded text (99% of modern textbooks) are processed at 20+ pages/second on CPU. No GPU, no VLM, no llama.cpp needed.

**Rationale**: The Shinkanzen N3 PDF and similar modern Japanese textbooks have clean embedded text layers. HPD was burning GPU time to OCR what was already available as text. For the rare scanned/OCR-only PDF, Marker's surya VLM can be optionally enabled via a `use_ocr` flag.

**Fallback**: If Marker detects garbled text on a page, it logs a warning. The Celery task can re-queue such pages with OCR enabled, or flag them for manual review.

### 2. New MarkerParser class replaces HPDFParser

**Decision**: Create a `MarkerParser` class with the same interface as `HPDFParser`:
- `convert_pdf(pdf_path, page_start, page_end, ...)` → returns `(markdown_text, json_blocks, errors)`
- Supports `progress_callback` and `cancel_check` (same signatures as HPD)

**Rationale**: The Celery task, API, and progress system remain unchanged. Only the parser internals swap out. This is a classic adapter pattern.

### 3. Marker JSON output maps to ContentBlock records

**Decision**: Marker's JSON output format (typed block tree with polygon coordinates) maps directly to the existing `ContentBlock` model:

```
Marker JSON block → ContentBlock
  block_type: "SectionHeader" → BlockType.header
  block_type: "Table"         → BlockType.table
  block_type: "Text"          → BlockType.paragraph
  block_type: "ListGroup"     → BlockType.list
  block_type: "Picture"       → BlockType.image_caption
  polygon coordinates         → bbox
```

**Rationale**: This eliminates the regex `<BLOCK>` parsing in `_save_content_blocks`. The JSON is machine-readable and unambiguous. No regex brittleness.

### 4. Remove HPD model and XPU dependencies

**Decision**: Delete `backend/model/` (2.81GB), remove `torch` XPU packages, remove `run_worker_gpu.py`. The GPU worker launch script is replaced by a simpler CPU worker script.

**Rationale**: Marker on CPU is faster than HPD on GPU. There is no reason to keep the GPU dependency. Docker `celery-worker` service can now handle all parsing — no more host-side worker needed.

### 5. Keep progress heartbeat and cleanup logic

**Decision**: The existing progress heartbeat (initial Redis write), cascading task cleanup, and completion-before-DB-save patterns remain unchanged. They were built to fix generic Celery task lifecycle issues and apply regardless of the parser.

### 6. Marker output format selection

**Decision**: Marker is invoked with `--output_format markdown,json`. The markdown goes to MinIO (for display/download), the JSON goes to the ContentBlock parser (for DB storage). Both formats come from a single Marker run — no extra cost.

### 7. Installation

**Decision**: `pip install marker-pdf` added to backend requirements. No additional system dependencies needed for CPU fast mode. The `surya` VLM is an optional dependency.

## Testing Decisions

### What makes a good test

- Test the MarkerParser interface, not Marker internals
- Use the existing PDF test fixtures
- Verify output quality: no repeated lines, correct Japanese characters, table detection
- Measure speed: a 10-page parse should complete in <5 seconds on CPU

### Test cases

| # | Test | Seam | Expected |
|---|------|------|----------|
| 1 | Convert Shinkanzen N3 (10 pages) with Marker | `MarkerParser.convert_pdf()` | Returns valid markdown, 0 repeated lines, correct JP chars |
| 2 | Marker output → ContentBlock mapping | Internal mapping function | JSON blocks map to correct BlockType values |
| 3 | Marker with page range (1-5) | `convert_pdf(page_start=1, page_end=5)` | Returns 5 pages only |
| 4 | End-to-end: upload → parse → get document | `POST /upload` → poll → `GET /{id}` | Document status → completed, blocks populated |
| 5 | Scanned PDF (no text layer) with OCR enabled | `convert_pdf(use_ocr=True)` | Falls back to surya VLM OCR |
| 6 | TOC extraction from Marker metadata | StructureExtractor with Marker JSON | All 29 chapters detected |

### Prior art

- The existing `test_model.py` pattern (test parser in isolation)
- The existing `structure_extractor.py` test (run on real data, assert chapter count)
- The curl-based API tests from the debugging sessions

## Out of Scope

- **Multi-language OCR optimization**: Marker already supports all languages the user needs (Japanese, English, Chinese, Vietnamese). No custom language models needed.
- **surya VLM GPU acceleration**: The VLM is optional and only needed for scanned PDFs. GPU acceleration for the VLM (via vLLM/CUDA) is out of scope — Intel Arc is not supported by vLLM, and CPU fallback via llama.cpp is acceptable for the rare OCR-only case.
- **Real-time collaborative editing of parsed documents**: Users view parsed content read-only. Editing parsed output is a separate feature.
- **Streaming parse progress from Marker**: Marker runs as a batch process. Per-page progress is approximated by counting pages processed vs total. The existing progress heartbeat pattern is sufficient.
- **Removing PyMuPDF dependency**: PyMuPDF is still used for page counting and metadata extraction (lightweight operations). Only the heavy OCR path is removed.

## Further Notes

- The HPD model directory (`backend/model/`, 2.81GB) should be deleted after the migration is verified. It's in `.gitignore` already.
- The `run_worker_gpu.py` and `setup_gpu.bat` scripts become obsolete and should be removed.
- The Docker `celery-worker` service can now handle all parsing with `--concurrency=4` (CPU-bound, parallel-safe) instead of the previous `--concurrency=1` (GPU-bound).
- Existing documents parsed with HPD remain in the database. Their quality will be lower than new Marker-parsed documents. A re-parse button could be added in the future.
- The StructureExtractor TOC parser should be updated to use Marker's built-in TOC metadata instead of regex-scanning markdown text. This is a separate improvement ticket.
