# Spec: HPD-Only Markdown Pipeline — Drop Hybrid, Store Usable Markdown

**Status**: ready-for-agent
**Created**: 2026-08-01
**Supersedes**: `specs/005-hpd-markdown/` (premise invalidated by real output inspection)
**Parent**: 001-lingua-notebook (PDF parsing subsystem)

## Problem Statement

The parsed document shown to the user (verified against a real Shinkanzen N3 parse on 2026-08-01) is not usable markdown. From the user's perspective:

1. **Every page renders as one giant "paragraph" block** — no structure. The frontend shows `paragraph / Page 2 / <entire page as one run-on blob>`. Page titles, tables, and lists are indistinguishable.
2. **Page numbers are off by one** — a 5-page PDF stores blocks labeled Page 2–6. The cover page shows as "Page 2".
3. **Markdown tables render as raw pipes** — `| 目次 Contents | 日本語 |` shows literally as text; the frontend injects `content_markdown` via `dangerouslySetInnerHTML` with no markdown renderer, so `|` and `---` appear verbatim.
4. **Hybrid mode is a silent no-op** — the parse recorded `parse_method: hybrid_hpd_qwen` but every page's content is 100% HPD-quality output (identifiable HPD errors like 語彚→語彙, 変化→変化, garbled English spacing). Qwen-VL never replaced any page. Hybrid adds 30-min parse times for zero benefit.
5. **Spec 005's premise was wrong** — the stored output contains **no `<BLOCK>/<CHILD>` tags at all**. The current HPD prompt (which asks for `|--|` markdown tables) makes the model emit plain markdown directly. There is nothing to "strip tags" from; the hpd_to_markdown.py adaptation in spec 005 targeted a format that no longer exists.

The stored content therefore cannot be chunked into meaningful units for the RAG knowledge base: one 2,648-char paragraph is not a retrievable unit.

## Solution

A single, honest OCR path: **text-layer PDFs → PyMuPDF; scanned PDFs → HPD → clean markdown → typed content blocks → frontend renders markdown properly.**

- Remove the hybrid/Qwen-VL re-parse routing entirely (it never delivered value and doubled parse time).
- HPD's output is already markdown-ish (tables come out as `| col | col |`). Add a **markdown → typed block parser** that recognizes what HPD actually emits: table rows, heading-like lines, list items, and paragraphs.
- Fix the page-numbering bug so stored blocks carry the PDF's real page numbers.
- Replace the frontend's raw-HTML injection with a real markdown renderer so tables and headings display as such.
- Accept HPD's ~85% Japanese accuracy as the production ceiling for now; the Stage 2 text-only LLM fixer (Qwen2.5-3B, separate spec) repairs OCR errors from the resulting markdown later.

## User Stories

1. As a language learner viewing a parsed document, I want each page to appear as multiple distinct, labeled blocks (header, table, list, paragraph), so that the book's structure is visible instead of one run-on blob.
2. As a language learner, I want tables in the page to render as real tables (with columns and borders), so that vocabulary lists and conjugation tables are actually readable.
3. As a language learner, I want the block labels to match the PDF page number shown on the original page, so that I can find content back in the book.
4. As a developer building the RAG knowledge base, I want chunkable units (tables, lists, paragraphs) per page, so that retrieval works on meaningful content instead of 2,000-char blobs.
5. As a developer, I want the parse pipeline to have exactly one OCR route, so that I can predict behavior, cost, and timing for any upload.
6. As a developer, I want no silent no-ops: if a mode can't deliver, it should not exist, so that `parse_method` always truthfully describes what ran.
7. As a developer, I want the page splitter to derive page numbers from the actual `--- Page N ---` markers, so that page attribution is correct even when a page yields no blocks.
8. As a language learner, I want re-uploading a document to produce the same improved quality, so that previously uploaded books gain the upgrade.
9. As a developer, I want the worker to be restartable after code changes without leaving stale behavior, so that fixes actually reach users (restart becomes part of the release checklist).
10. As a developer, I want the Qwen-VL integration kept on disk but unwired, so that Stage 2 can reuse its llama-server infrastructure without re-inventing it.

## Implementation Decisions

### 1. Single OCR route (drop hybrid)

**Decision**: `parse_pdf_hybrid` keeps only two branches: text-layer PDFs → PyMuPDF extraction; everything else → HPD OCR. The `mode` parameter's "balanced"/"hybrid" values are removed from routing. The API keeps accepting `mode` for backward compatibility but the worker ignores it (or the parameter is removed from the frontend only). Qwen-VL and Marker routing code paths are deleted from the parser; the `qwen_vlm_parser` module file remains for Stage 2.

**Rationale**: The evidence (parse method said hybrid, content was 100% HPD) shows the fallback chain silently degraded. A single path is predictable. Stage 2 replaces the quality role that hybrid claimed.

### 2. Markdown → typed block parser service

**Decision**: New service (in the existing services package) exposing one seam:

- `parse_page_blocks(page_text: str) -> list[Block]` where `Block` carries `block_type`, `bbox` (None), `content` (clean markdown text).

Recognition rules, based on what HPD actually emits today (verified from the Shinkanzen N3 parse):
- Consecutive lines matching `| ... |` (or a `| --- |` separator) → one `table` block, kept as markdown table text.
- Standalone short heading-like lines (e.g. はじめに, ■本書の特徴, lines ending with `：` or `:` that don't end in sentence punctuation) → `header`.
- Lines starting with list markers (`・`, `-`, `*`, `1.`, `①`) → `list` block.
- Everything else → `paragraph`.
- Blocks are emitted in reading order (the order HPD produced them).

**Rationale**: This targets the format that actually exists (verified output), unlike spec 005's tag-stripping premise. Heuristics are conservative: misclassifying a heading as a paragraph is acceptable; merging table rows into a paragraph is not (tables must survive for RAG).

### 3. Correct page numbering

**Decision**: The worker's page splitter extracts the page number from the `--- Page N ---` marker itself (regex capture) instead of deriving it from the array index. Blocks carry the true PDF page number. `total_pages` reflects the highest parsed page number.

**Rationale**: The current index-based arithmetic is wrong by construction (the pre-page-1 split element consumes index 0).

### 4. Frontend renders real markdown

**Decision**: Add a markdown renderer (react-markdown + remark-gfm) to the frontend; replace `dangerouslySetInnerHTML` with the renderer for block content. Tables then render via GFM tables. The mode selector in the upload UI is removed (single mode now); DPI and page-range controls stay.

**Rationale**: GFM is the markdown dialect HPD emits (pipe tables). react-markdown is the standard React choice; remark-gfm enables table rendering.

### 5. Worker restart discipline

**Decision**: The worker's stale-code problem (this session's recurring failure) is addressed operationally, not in code: restarting the worker after backend changes becomes a documented step in the release checklist, verified by the "Model Path:" startup log line.

**Rationale**: No code change can make a running Celery worker pick up new code.

## Testing Decisions

### What makes a good test

- **Service seam**: feed the parser a known markdown string (table rows, heading line, list, paragraph mixed) and assert the typed block sequence. This is the single test seam for conversion quality.
- **Golden fixture**: use the real HPD output captured from the Shinkanzen N3 parse (already retrieved from storage) as the fixture — asserts tables survive, headings are typed, and the full page does not collapse into one block.
- **Worker/API seam**: upload → parse → fetch document, asserting `page_number` values equal the PDF's real pages and block types are non-uniform.
- **Frontend**: render a block whose content is a markdown table and assert a `<table>` element appears in the DOM (component test).

### Test cases

| # | Test | Seam | Expected |
|---|------|------|----------|
| 1 | `parse_page_blocks` with mixed content (heading, table, list, paragraph) | Service unit | 4 blocks in reading order with correct types |
| 2 | Table with `| --- |` separator rows | Service unit | Single `table` block, markdown table text intact |
| 3 | Golden fixture: real Shinkanzen N3 page from the 2026-08-01 parse | Service unit | ≥3 blocks per page, tables preserved, no single giant paragraph |
| 4 | Page splitter with 5-page markdown | Worker unit | Blocks carry page numbers 1–5 (not 2–6) |
| 5 | End-to-end: upload scanned PDF → parse → GET document | API | Blocks typed, page numbers correct, content clean |
| 6 | Re-parse after re-upload | API | Same quality as first parse |
| 7 | Frontend renders `| a \| b |` as `<table>` | Component | Table element present, no literal pipes in visible text |

### Prior art

- `tests/` structure exists with unit/integration/contract packages (currently empty).
- The real parse artifacts (document `00f26d1a-ac6f-4528-8a39-44266df520b5`: combined markdown in storage + content blocks in DB) serve as the golden fixture source.

## Out of Scope

- **Stage 2 LLM fixer** (Qwen2.5-3B repairing Japanese OCR errors) — separate spec; consumes this pipeline's output.
- **Marker/surya integration** — impractical on Intel Arc (SSM bottleneck), previously concluded.
- **hpd_to_markdown.py adaptation** — spec 005's approach; premise invalidated (no `<BLOCK>` tags in current output).
- **Extending `BlockType` enum** — taxonomy change touches the frontend; defer.
- **Formula/LaTeX normalization** — HPD output showed no formula blocks in the sampled pages; revisit if math-heavy documents appear.
- **Bounding-box support** — HPD's markdown-mode output carries no bboxes; blocks store `bbox: None`.

## Further Notes

- The parse that informed this spec: 5 pages, 30 minutes, `hybrid_hpd_qwen`, 0 errors — but content 100% HPD. This is the "silent no-op" evidence that justifies dropping hybrid.
- HPD's current prompt already asks for `|--|` markdown tables (in the HPD parser wrapper), which is why tables arrive as markdown — the parser service must not fight that.
- Storage: `combined.md` remains the canonical parsed artifact; blocks in the DB are derived from it. The block parser should ideally share one source of truth with whatever Stage 2 later consumes.
- Expected accuracy stance: HPD ~85% Japanese is accepted now; Stage 2's LLM repair (85.4% → 94.8% per JaPOC research) is the planned quality upgrade and works on this pipeline's markdown output.
