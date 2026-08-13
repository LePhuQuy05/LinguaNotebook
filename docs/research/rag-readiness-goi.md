# RAG Readiness: GOI.pdf (Shinkanzen N3 語彙) — 2026-08-11

Assessment of whether the PaddleOCR-VL output (doc `16116abe`) can feed the RAG
pipeline as-is, what preprocessing it needs, and what the RAG/lesson pipeline
is missing. Grounded in the actual output (3,693 ContentBlocks, 186 pages,
416,243 chars of Japanese) and the current backend code.

## 1. Output quality — text is RAG-ready, markup is not

The OCR text itself is high quality: vocab entries with furigana, example
sentences, exercises with answer options, correct page markers (1–186),
sensible block typing (paragraph 1841 / header 1315 / list 537). Measured
noise that must be stripped before embedding:

| Noise | Measured | Impact |
|---|---|---|
| `<img src="imgs/...">` refs (not downloaded) | 75 blocks (2%) | junk tokens in embeddings |
| `<div style="...">` wrappers | 88 occurrences | junk tokens; breaks chunk cohesion |
| Numbered-list order scrambled | page 3: ①⑤②④③ | OCR visual order ≠ reading order; hurts lesson coherence (low impact for retrieval) |
| Furigana lines separate from kanji | common | *feature* for learning — keep |
| `page_start` payload | always 1 (chunker never sets it) | page-accurate citations impossible |

**Verdict:** strip HTML/img markup, thread page numbers into chunk metadata,
then the output is ready. No re-OCR, no de-skew, no DPI work needed — the
cloud OCR already handled that.

## 2. RAG pipeline — search side is built, wiring is missing

What exists and is sound:
- `services/rag_service.py` — hybrid dense (BGE-M3, multilingual → Japanese
  OK) + sparse (BM25) with RRF fusion, metadata filters.
- `utils/chunker.py` — structure-aware chunking (headers/tables/lists intact,
  paragraphs merged 50–500 tokens, 1-sentence overlap) — matches the research
  sweet spot (256–512 tokens, structural boundaries).
- `services/embed_service.py` — BGE-M3 dense + BM25 sparse upsert into
  per-user Qdrant collections.

What is **missing / broken** (the actual work):
1. **`embed_document` is never dispatched** — parse saves ContentBlocks and
   stops. Qdrant is empty; `hybrid_search` returns nothing. This is the #1
   blocker for "next step RAG".
2. **`embed_worker.py` has the same per-call event-loop bug** we fixed in
   parse_worker ("proactor.send on None" on the 2nd doc in one process) —
   must use the persistent `_get_event_loop()` pattern before enabling.
3. **`page_start` metadata** — `Chunk.metadata` never carries the page
   number; every Qdrant payload says `page_start: 1`. Fix in the chunker.
4. Lesson queries are English generic strings ("key terms and concepts")
   against Japanese content — BGE-M3 bridges it, but Japanese queries
   derived from the curriculum match better.

## 3. Lessons — structure map > summary, and neither exists yet

`lesson_service.generate_lesson` today: N generic queries → N random chunks
→ canned questions with the raw chunk as the answer. No LLM anywhere in the
backend. The result would be incoherent (random vocab + random exercises,
out of curriculum order).

Research consensus (sources in conversation report):
- Curriculum alignment comes from **knowledge graphs / structured outlines**,
  not raw text summaries (EduAI Helper; Study-Labs' map-reduce outline
  synthesis).
- Structure-aware chunking is worth **+25pp accuracy** over naive chunking on
  curriculum documents (Western Sydney, AusDM 2025).
- Metadata + hybrid retrieval beat embedding tweaks ("metadata is king").

The Shinkanzen book is chapter-structured (第1部 話題別, 第2部 性質別 — visible
in the OCR'd front matter). The **table of contents is in the book** (pages
~4–6): extracting it gives a free curriculum map (chapter → topic → page
range) with zero LLM. Rule-based now; LLM (Qwen, unwired Stage 2) later.

## 4. Recommended order of work

1. **Clean blocks before chunking**: strip `<img>`/`<div>` markup in
   `parse_worker._save_content_blocks` (or a `clean_markdown` util) + unit
   test. Small, immediate.
2. **Wire parse → embed**: dispatch `embed_document` from `parse_pdf_task`
   after blocks save; fix embed_worker's event loop (persistent loop).
3. **Page metadata**: thread `page_number` through `SmartChunker` into the
   Qdrant payload.
4. **Curriculum map**: extract TOC from pages 4–6 → `DocumentStructure`
   table (chapter/topic/page_range) — enables "this week = chapter 3 (天気)".
5. **Lesson generation v2**: schedule-driven: pick chapter → retrieve its
   chunks → compose items (vocab entries + their exercises from the same
   section) — rule-based first, LLM later.

## 5. Open questions (next experiments)

- H1: stripping `<img>`/`<div>` noise measurably improves retrieval (proxy:
  Japanese query "天気" retrieves the weather chapter; inspect top-k).
- H2: TOC-derived chapter map produces more coherent lessons than random
  retrieval (proxy: lesson item source-page spread within one chapter vs
  across the whole book).
- H3: Japanese queries beat English template queries on Japanese content.
