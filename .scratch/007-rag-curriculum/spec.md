# 007 — RAG pipeline wiring + curriculum-driven lessons

**Status:** ready-for-agent

## Problem Statement

The OCR pipeline (spec 006 + PaddleOCR-VL cloud backend) now produces high-quality typed ContentBlocks (verified: 3,693 blocks, 186 pages, 416k chars of Japanese for GOI.pdf). But the RAG stage is not connected: `embed_document` is never dispatched, so Qdrant is empty and `hybrid_search` returns nothing. Lessons (`generate_lesson`) fetch random chunks via generic English queries and paste them as canned answers — no curriculum structure, no coherence.

## Solution

From the user's perspective: upload a book once → the knowledge base becomes searchable automatically → daily lessons come from one chapter of the book in order (vocab + its exercises), with page-accurate references.

## User Stories

1. As a user, I want my uploaded book's content to appear in the searchable knowledge base without extra steps, so that RAG features work after parse completes.
2. As a user, I want the chunks in my knowledge base to be free of OCR markup noise (`<img>`/`<div>` tags), so that retrieval quality isn't diluted.
3. As a user, I want each retrieved chunk to carry its real page number, so that lessons and answers can cite "page 42" accurately.
4. As a user, I want lessons drawn from one chapter of my book (vocabulary entries and their exercises together), so that each day's study is coherent and follows the book's curriculum.
5. As a user, I want the daily lesson to know which chapter it came from, so that progress through the book is trackable.
6. As a developer, I want the embedding worker to survive repeated documents in one process, so that batch processing doesn't crash on the second document.

## Implementation Decisions

- **Cleaning**: a `clean_markdown(text)` utility strips HTML tags (`<img …>`, `<div …>`, others) from block content. Applied once in `parse_pdf_task` right after parsing, before the MinIO `combined.md` upload and the block save — both artifacts derive from the cleaned string, so blocks and `combined.md` stay clean at the source.
- **Wiring**: `parse_pdf_task` dispatches `embed_document` (via `embed_document_task.delay(document_id, user_id)`) after `_save_content_blocks` succeeds. The embed worker must use the persistent `_get_event_loop()` pattern from `parse_worker` — its current per-call `new_event_loop()`/`close()` has the same "proactor.send on None" crash on the second document in one process.
- **Page metadata**: `SmartChunker.chunk_blocks` receives blocks with `page_number`; `Chunk.metadata` gains `page_start`/`page_end`; `embed_and_index_chunks` writes them into the Qdrant payload (currently hardcoded `page_start: 1`).
- **Curriculum map**: new `DocumentStructure` model (document_id, part, chapter, topic, page_start, page_end, order). Extraction is rule-based from the book's table of contents pages (Shinkanzen N3: 第1部 話題別 / 第2部 性質別 with chapter titles) — no LLM required. Page ranges are resolved from `--- Page N ---` markers.
- **Lessons v2**: `generate_lesson` walks the curriculum map (schedule → next chapter), derives a Japanese search query from the chapter topic, filters `hybrid_search` to the chapter's document + page range, and composes items so vocabulary entries and their exercise sets come from the same section. No LLM — rule-based composition; LLM composition stays out of scope (Stage 2, `qwen_vlm_parser` is unwired by design).

## Testing Decisions

- Unit: cleaning utility (img/div/HTML stripped, Japanese text intact); chunker page metadata; curriculum-map extraction against the real GOI.pdf TOC pages as a golden fixture; lesson item source-page spread within one chapter.
- Integration/E2E: parse a scanned PDF → blocks clean → `embed_document` runs → Qdrant collection has points → `hybrid_search("天気")` retrieves the weather chapter. Re-run the worker twice on two documents (regression for the persistent-loop fix).
- Prior art: `tests/unit/test_parse_worker.py` (persistent loop regression), `tests/unit/test_paddle_ocr_service.py` (mocked HTTP), golden-fixture pattern from ticket 006-01.

## Out of Scope

- LLM-based lesson composition / markdown fixing (Stage 2; Qwen module stays unwired).
- Downloading OCR result images (`markdown.images`).
- Difficulty estimation beyond the existing hardcoded value.
- Frontend changes (existing lesson/documents UI keeps working against the same API).
- Batch re-indexing of already-parsed documents (a one-off script can be written ad hoc).

## Further Notes

- Findings and measurements: `docs/research/rag-readiness-goi.md` (2026-08-11).
- The chapter map is book-type-specific for Japanese textbooks (第N部/第N章 patterns); the extractor should be conservative — unknown structure → no map, lessons fall back to current behavior.
