# 05 — Chapter-driven daily lessons

**What to build:** Today `generate_lesson` fetches random chunks via generic English queries and pastes them as canned answers — incoherent, out of curriculum order. After this ticket: a lesson picks the schedule's next chapter from the curriculum map, builds a Japanese search query from the chapter topic, retrieves the chapter's chunks (filtered by document + page range), and composes items so vocabulary entries and their exercise sets come from the same section, in book order.

**Blocked by:** 03, 04

**Status:** ready-for-human

- [x] Lesson generation walks the curriculum map (schedule → next chapter after the last completed one)
- [x] Search query derived from the chapter topic in Japanese (e.g. weather chapter → 天気-related query)
- [x] `hybrid_search` called with the chapter's document_id + page-range filter
- [x] Items composed from the same section: vocab entries and their exercises stay together; item order follows the chapter's page order
- [x] No curriculum map / no schedule → falls back to current random-retrieval behavior
- [x] Unit tests: lesson items' source pages all fall inside the chosen chapter's range

## Comments

2026-08-14 (follow-up) — curriculum extractor now handles 章-based books too (8e90001). The TOC scan only read 課-based TOCs; a new upload — Shinkanzen N3 Kanji (192p, doc `550b5b66`) — came back with 0 `document_structures` rows because its chapters are `N章` and its TOC pages (5–7) break the dotted page anchors across lines. `extract_curriculum` now falls back to body headings (`## N章 <title>`, full-width-digit + OCR-space tolerant), skipping test/quiz/まとめ/復習 and multi-chapter spans, deduping repeated headings. 20 chapters extracted (p8–192) and backfilled; `/documents/{id}/structures` serves them; `/lessons/daily` stays chapter-driven (GOI ch1, 5 items). 6 new unit tests; 137 backend tests pass.

2026-08-14 — completed, live-verified. `/lessons/daily` now attributes the lesson to its chapter (`document_id`, `chapter_num`, `chapter_title`, `document_filename`), and every item carries a `source` block (page_start/page_end/token_count/block_type/content) resolved from the Qdrant point id via `rag_service.get_chunk_sources` (extracted from the route handler to a testable service seam). Items also now include `correct_answer`, which the flashcard reveal needs (previously omitted from the daily response). Live: chapter 1 `人間関係1：家族と友達、性格`, 5 items all sourced from page 3. Tests: `test_lesson_service.py` (chapter walk, page-scoped retrieval, fallback), `test_rag_service.py::TestGetChunkSources`.

2026-08-13 — Implemented, 11 unit tests green, two-axis code review applied:
`_next_chapter` (most-advanced book first, recycle last when all done),
`_chapter_query` (Japanese prefix up to first Latin letter or colon → 天気の言葉),
chapter retrieval scoped by document_id + page range, items sorted in book
order, item type follows schedule content_types (round-robin). Review fixes:
test fixture pages moved inside the chapter range (AC6), weak most-advanced
test made meaningful, magic numbers named, `sorted()` deduped, `_next_chapter`
typed. Bug found by tests: `ItemType("vocabulary")` raised (no such member) —
mapped vocabulary → flashcard via `_ITEM_TYPE_BY_CONTENT_TYPE`. E2E (real
Schedule → lesson items from one chapter) pending Qdrant embed (ticket 02).
