# Spec: Hybrid PDF Parser — Text Extraction + OCR Fallback

**Status**: ready-for-agent
**Created**: 2026-07-28
**Parent**: 001-lingua-notebook
**Supersedes**: 003-marker-migration (archived — Marker not viable without NVIDIA GPU)
**Triage**: ready-for-agent

## Problem Statement

The HPD OCR pipeline has fundamental quality issues for Japanese language textbooks. However, after extensive evaluation, a full replacement with Marker proved impractical due to infrastructure constraints (Intel Arc GPU not supported by vLLM, llama.cpp CPU inference too slow for production, complex model dependency chain).

The real problem is more nuanced: **the system blindly OCRs every PDF even when embedded text is available**. Many PDFs (academic papers, digitally-produced textbooks, web-saved documents) have clean embedded text layers that can be extracted 100% accurately in milliseconds — but the current pipeline always routes to HPD, burning GPU time and introducing OCR errors where none are needed.

For the PDFs that DO need OCR (scanned textbooks like Shinkanzen N3), HPD quality has been improved through multiple fixes (disabled MTP speculative decoding, repetition penalty, degeneration filter). However, Japanese character accuracy remains ~80-85% — acceptable for RAG search but not for study material generation.

## Solution

A **hybrid PDF parser** that auto-detects the PDF type and routes accordingly:

1. **Text-based PDFs** → PyMuPDF text extraction (0.04s/page, 100% accurate, CPU-only)
2. **Scanned/image-based PDFs** → HPD OCR (GPU-accelerated, with quality fixes applied)

The detection happens transparently before parsing begins. The frontend and API are unaware of which method was used — they receive the same markdown output format. A `method` field in the logs enables debugging.

### Marker evaluation outcome

Marker (Apache 2.0) was evaluated as a potential HPD replacement. It offers superior OCR quality via the surya VLM (Qwen3.5-based, 632M params) and native markdown/JSON/table output. However, it could not be deployed due to:

1. **GPU requirement**: surya VLM requires NVIDIA GPU (vLLM) for reasonable speed. Intel Arc is not supported. CPU inference via llama.cpp takes 5-10 minutes per page — slower than HPD on GPU.
2. **Infrastructure complexity**: Requires llama-server binary with Qwen3.5 architecture support, multimodal projector files, and proper shared library paths.
3. **First-run cost**: Model downloads (~2GB) from HuggingFace on first run. Subsequent runs are fast once cached.

**Decision**: Marker evaluation is deferred until either (a) an NVIDIA GPU becomes available, or (b) llama.cpp CPU inference becomes fast enough for production use. The hybrid parser architecture is designed so that Marker can be added as a third routing option without changing any other code.

## User Stories

1. As a language learner uploading a digitally-produced PDF textbook, I want it to parse in under 1 second with 100% accurate text, so that I can start studying immediately.

2. As a language learner uploading a scanned PDF textbook, I want the best available OCR quality on my Intel Arc GPU, so that even image-based documents are usable.

3. As a language learner, I don't want to think about whether my PDF is text-based or scanned — the system should figure it out automatically.

4. As a self-hoster running on CPU-only hardware, I want text-based PDFs to work without any GPU, so that I can use the app on any machine.

5. As a developer maintaining LinguaNotebook, I want to eventually add Marker as a third parsing option when infrastructure allows, without rewriting the entire pipeline.

6. As a language learner, I want to see feedback about which parsing method was used (text extraction vs OCR), so that I understand why one document parsed instantly and another took minutes.

7. As a developer, I want the parser to degrade gracefully — if GPU is unavailable, text-based PDFs still work on CPU, and scanned PDFs return a clear error rather than timing out.

## Implementation Decisions

### 1. Text layer detection heuristic

**Decision**: Sample 3 pages (first, 1/3, 2/3 through the document) using PyMuPDF's `get_text("text")`. If the average character count exceeds 100 chars/page, classify as text-based. Otherwise, classify as image-based (scanned).

**Rationale**: A scanned page returns only footer text (~30 chars like "nihongopro.net"). A text-based page returns hundreds of characters of content. The 100-char threshold cleanly separates the two categories. Sampling 3 pages distributed across the document catches cases where only some pages have text.

**Edge case**: Mixed PDFs (some pages text, some images) default to OCR for safety. The text detection is conservative — if any sampled page appears image-based, the whole document routes to OCR.

### 2. PyMuPDF extraction for text-based PDFs

**Decision**: Use `fitz.Page.get_text("text")` with default reading order. Output is wrapped in the same `--- Page N ---` format as HPD for compatibility with `_save_content_blocks`.

**Rationale**: PyMuPDF is already a project dependency. Its text extraction preserves reading order, handles Unicode (Japanese/Chinese/Vietnamese), and runs in <0.05s per page. No model loading, no GPU, no new dependencies.

**Limitation**: No block-level metadata (header/table/list detection). All content is stored as `BlockType.paragraph`. This is acceptable because text-based PDFs have their structure in the embedded text formatting, which PyMuPDF preserves.

### 3. HPD OCR for scanned PDFs

**Decision**: Keep the existing HPD pipeline with all quality fixes applied:
- `use_mtp=False` (no speculative decoding)
- `repetition_penalty=1.15, no_repeat_ngram_size=10`
- `_deduplicate_repeated_lines()` post-processing

**Rationale**: These fixes eliminated the most severe quality issues (infinite repetition loops). Remaining Japanese character errors (~15-20%) are inherent to the 1B-param model architecture and cannot be fixed without a better model.

### 4. Parser interface contract

**Decision**: All parsers implement the same signature:
```python
(pdf_path, page_start, page_end, dpi, progress_callback, cancel_check) 
  → (markdown_text, errors, method_name)
```

**Rationale**: The Celery task doesn't need to know which parser is being used. Adding a new parser (Marker, Tesseract, etc.) requires only adding a new routing branch in `parse_pdf_hybrid()`.

### 5. Worker changes

**Decision**: `parse_pdf_task` no longer calls `_get_parser()` at startup. Instead, it calls `parse_pdf_hybrid()` which handles model loading internally. HPD model is still lazy-loaded once per worker lifetime when first needed.

**Rationale**: For text-based PDFs, the HPD model is never loaded, saving 2GB VRAM and 5s startup time. The model is only loaded on the first scanned PDF the worker encounters.

### 6. Docker celery-worker capability

**Decision**: The Docker `celery-worker` service can now handle text-based PDFs without GPU. For scanned PDFs, the host GPU worker is still needed (Intel XPU). The `celery-worker` logs which method was used.

**Rationale**: This is a step toward fully Dockerized parsing. When Marker or another CPU-friendly OCR becomes viable, the Docker worker can handle all PDFs.

## Testing Decisions

### What makes a good test

- Test the routing decision, not the parser internals
- Use real PDFs from the project's MinIO storage
- Verify the method detection is correct for known PDF types

### Test cases

| # | Test | Expected |
|---|------|----------|
| 1 | Upload digital PDF with embedded text | Method = "text_layer", completes in <2s, 0 character errors |
| 2 | Upload scanned PDF (Shinkanzen N3) | Method = "ocr", uses HPD, standard OCR quality |
| 3 | Upload PDF with no text at all | Method = "ocr", falls back to HPD |
| 4 | Text detection on known scanned PDF | `_has_text_layer()` returns False |
| 5 | Progress heartbeat before first page | Frontend shows "Parsing... Page 0 of N" within 2s of upload |
| 6 | Completion signal before DB save | Frontend shows "completed" immediately after parsing, even if DB save takes longer |

### Prior art

- `backend/test_model.py` — test HPD model in isolation
- `backend/src/services/structure_extractor.py` — test with real OCR output, assert counts
- curl-based API testing from debugging sessions

## Out of Scope

- **Marker/surya VLM integration**: Evaluated and deferred. Will be reconsidered when NVIDIA GPU or faster CPU inference becomes available.
- **OCR quality beyond current HPD fixes**: Further HPD quality improvements require a different model architecture. The current fixes are the limit of what can be done with this model.
- **PDF-to-PDF conversion**: Output is markdown only. Reconstructing a formatted PDF is out of scope.
- **Multi-column PDF layout detection**: PyMuPDF extraction may mix columns on complex layouts. Layout-aware extraction is deferred.
- **Block type detection for text-based PDFs**: All content is stored as `paragraph`. Header/table/list detection for extracted text is deferred.

## Further Notes

- The Marker investigation was valuable despite not being deployed: it revealed that both user PDFs are image-based scans, confirmed that the text-layer detection heuristic works correctly, and established the infrastructure requirements for any future VLM-based OCR.
- The surya-ocr-2 model (1.18GB, Qwen3.5 architecture) is already downloaded and cached in the Docker container at `/root/.cache/huggingface/hub/`. When Marker integration is revisited, the model will not need to be re-downloaded.
- The `specs/003-marker-migration/` spec is archived in favor of this one. The architecture decisions from that spec informed the parser interface contract used here.
- The hybrid parser approach reduces average parse time from ~53s/page (GPU OCR) to <0.05s/page for any PDF with embedded text. For a typical 100-page digital textbook, this is the difference between 1.5 hours and 2 seconds.
