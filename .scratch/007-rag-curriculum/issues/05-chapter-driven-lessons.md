# 05 — Chapter-driven daily lessons

**What to build:** Today `generate_lesson` fetches random chunks via generic English queries and pastes them as canned answers — incoherent, out of curriculum order. After this ticket: a lesson picks the schedule's next chapter from the curriculum map, builds a Japanese search query from the chapter topic, retrieves the chapter's chunks (filtered by document + page range), and composes items so vocabulary entries and their exercise sets come from the same section, in book order.

**Blocked by:** 03, 04

**Status:** ready-for-agent

- [ ] Lesson generation walks the curriculum map (schedule → next chapter after the last completed one)
- [ ] Search query derived from the chapter topic in Japanese (e.g. weather chapter → 天気-related query)
- [ ] `hybrid_search` called with the chapter's document_id + page-range filter
- [ ] Items composed from the same section: vocab entries and their exercises stay together; item order follows the chapter's page order
- [ ] No curriculum map / no schedule → falls back to current random-retrieval behavior
- [ ] Unit tests: lesson items' source pages all fall inside the chosen chapter's range

## Comments

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
