# Spec: HPD Output → Proper Markdown Conversion

**Status**: ready-for-agent
**Created**: 2026-08-01
**Parent**: 001-lingua-notebook (PDF parsing subsystem)
**Context**: Follow-up to `specs/004-hybrid-parser/` and `docs/research/hpd-family-and-markdown-fixer.md`

## Problem Statement

The current pipeline discards most of the structured output that the HPD-Parsing model already produces. HPD emits a rich `<BLOCK>/<CHILD>` token stream carrying region categories (header, paragraph, table, list, title, footer, formula...), bounding boxes, and reading order. The worker's `_save_content_blocks` parses only 5 block types via a hand-written regex, drops everything else, and stores the raw `<BLOCK>`-tagged text as "markdown".

Consequences for the user:

1. **Lost structure**: headers, footers, page numbers, and titles are stored as generic paragraphs. Tables detected by HPD are flattened or garbled. Formula blocks are kept as raw text.
2. **No markdown formatting**: The stored `content_markdown` still contains `<BLOCK>`, `<CHILD>`, `[x1,y1,x2,y2]` noise that renders as garbage in the frontend.
3. **RAG quality ceiling**: The RAG knowledge base (next phase) chunks this noisy text — poor structure means poor retrieval.
4. **No formula normalization**: Unicode operators (≈, ≤, ×) stay as-is instead of LaTeX.

The model's own repository ships `eval/hpd_to_markdown.py` — a conversion tool that solves exactly this: it strips block tags, keeps all text in reading order, cleans formula tails, normalizes arithmetic to LaTeX, and emits per-page markdown. The pipeline currently ignores it.

## Solution

Replace the hand-written regex block parser with the model's own conversion logic (`hpd_to_markdown.py`), adapted into the codebase as a proper service module.

**Stage 1.5 (this spec)**: Parse the full `<BLOCK>/<CHILD>` stream → clean per-page markdown, preserving block categories so ContentBlock records keep their type. This is a **free quality improvement** — no new model, no new hardware, same 53s/page cost.

**Stage 2 (separate spec, optional)**: Feed Stage 1.5 output to a small text-only LLM (Qwen2.5-3B via llama.cpp SYCL) to repair remaining Japanese OCR errors using context. Documented in `docs/research/hpd-family-and-markdown-fixer.md`; not in scope here.

## User Stories

1. As a language learner viewing a parsed document, I want to see clean markdown without `<BLOCK>`, `<CHILD>`, or coordinate noise, so that the content is readable.

2. As a language learner, I want tables detected by HPD to render as markdown tables, so that vocabulary lists and conjugation tables are usable for study.

3. As a language learner, I want headers, titles, and footers to be typed correctly in the content blocks, so that the structure of the book is preserved.

4. As a developer building the RAG knowledge base, I want chunkable clean text per page, so that retrieval works on meaningful units.

5. As a developer, I want the formula handling (LaTeX normalization) to work, so that math-heavy pages (if any) are stored correctly.

6. As a language learner, I want existing documents to be re-parseable with the improved conversion, so that previously uploaded books gain the quality upgrade.

7. As a developer, I want the conversion logic to be a reusable service (not embedded in the worker), so that it can also be used by the Stage 2 fixer pipeline and future tooling.

## Implementation Decisions

### 1. New service module: HPD markdown converter

**Decision**: Create a `hpd_markdown` service module that wraps the conversion logic from the model's `eval/hpd_to_markdown.py`:

- `convert_prediction_to_markdown(pred: str) -> str` — the core `remove_block_fork_tags()` logic (split on `<BLOCK>`, keep text after `<CHILD>`, join in reading order, drop chart/seal blocks, clean formula tails, normalize arithmetic).
- `parse_blocks(pred: str) -> list[Block]` — returns typed blocks (category, bbox, content) so `_save_content_blocks` can store proper `BlockType` values AND keep the full reading-order text.

**Rationale**: The model's script is the reference implementation — verified to produce OmniDocBench-comparable markdown. Copying its logic into the codebase (with attribution) gives us the same quality without inventing a parallel regex. Making it a service module (not worker-embedded) lets Stage 2 and future tooling reuse it.

### 2. Block type mapping

**Decision**: Map HPD categories to existing `BlockType` enum where possible:

| HPD category | BlockType |
|---|---|
| `header` | header |
| `title` | header |
| `paragraph` | paragraph |
| `text` | paragraph |
| `table` | table |
| `list` | list |
| `image_caption` | image_caption |
| `footer`, `page_number` | paragraph (with bbox, but content kept) |
| `formula` | paragraph (content normalized to LaTeX) |
| everything else | paragraph |

**Rationale**: The current `BlockType` enum has 5 values; extending it is out of scope (would touch the frontend). Unknown categories degrade to paragraph while still preserving content — the important fix is content preservation + reading order, not taxonomy.

### 3. `_save_content_blocks` rewrite

**Decision**: The worker's `_save_content_blocks`:
- Uses the new service's `parse_blocks()` instead of the hand-written regex
- Stores each typed block as a ContentBlock with correct `block_type` and `bbox`
- **Preserves all text** — no block dropped, reading order kept
- Still deduplicates degeneration (existing `_deduplicate_repeated_lines` runs first)

**Rationale**: Same DB schema, same API, same frontend. Only the parsing internals change. The seam is the worker's block parser.

### 4. Re-parse support

**Decision**: A re-parse is achieved by re-uploading the document (existing flow). No new endpoint. The document detail page already handles re-upload.

**Rationale**: YAGNI — a dedicated "re-parse" endpoint adds API surface for a flow users already have (delete + re-upload). Revisit if users complain.

### 5. Text-layer PDFs unaffected

**Decision**: PDFs with embedded text (PyMuPDF path) keep their current conversion (plain `--- Page N ---` sections). The HPD markdown converter only applies to OCR'd (image-based) PDFs.

**Rationale**: PyMuPDF text is already clean; the converter targets HPD's noisy block stream.

## Testing Decisions

### What makes a good test

- Test the conversion at the service seam: feed a known `<BLOCK>/<CHILD>` stream, assert the markdown output.
- Test the worker end-to-end at the existing API seam: upload → parse → fetch document, assert blocks are typed and content is clean.
- Use a real HPD prediction sample captured from the user's Shinkanzen N3 parse as the fixture (golden test).

### Test cases

| # | Test | Seam | Expected |
|---|------|------|----------|
| 1 | `convert_prediction_to_markdown` with sample `<BLOCK>` stream | Service unit | Output has no `<BLOCK>/<CHILD>` tags, text in reading order |
| 2 | `parse_blocks` with header + table + paragraph blocks | Service unit | 3 blocks with correct types + bboxes |
| 3 | Formula block with `≈` / `×` | Service unit | Unicode ops → LaTeX (`\approx`, `\times`) |
| 4 | End-to-end: upload scanned PDF → parse → GET document | API | Blocks typed correctly, content clean markdown, no tag noise |
| 5 | Re-parse after re-upload | API | Same quality as first parse |
| 6 | Regression: document with `_deduplicate_repeated_lines` still collapses degeneration | Worker unit | Repeated lines collapsed, rest preserved |

### Prior art

- `backend/model/eval/hpd_to_markdown.py` — the reference implementation being adapted
- `docs/research/hpd-family-and-markdown-fixer.md` — the research justifying this approach
- Existing `_save_content_blocks` + `_deduplicate_repeated_lines` — the code being replaced/extended

## Out of Scope

- **Stage 2 LLM fixer** (Qwen2.5-3B repairing Japanese OCR errors) — separate spec, per research doc.
- **Extending `BlockType` enum** — taxonomy change touches frontend; defer.
- **PaddleOCR-VL integration** — CPU-only on this hardware; not faster than HPD; documented as fallback.
- **Table structure detection beyond HPD's own output** — we format what HPD detects; we do not add a table-detection model.
- **Formula rendering** — we normalize to LaTeX text; rendering is a frontend concern.

## Further Notes

- The reference script is MIT-licensed (part of the HPD model repo); adapting its logic into the codebase is compatible with the project's MIT license.
- The Stage 2 fixer (research doc) estimates ~90-95% effective Japanese accuracy after LLM repair vs ~85% raw — but requires A/B validation on 10-20 pages first. This spec's Stage 1.5 improvement is independent of that validation and should land first.
- `_deduplicate_repeated_lines` must run BEFORE block parsing (it does today) — degeneration collapse then block typing.
- The `hpd_to_markdown.py` script has CLI entry points (`convert_json`) we won't use; only the pure functions (`remove_block_fork_tags` and helpers) are adapted.
