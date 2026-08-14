# 02 — Confidence gate + content-association cross-check

**What to build:** The rule scan measures how confident it is by checking whether candidate chapter titles from the TOC also reappear in the document's body. The cross-check is soft — no chapter is dropped because OCR made its title differ. High confidence → the TOC result is used as-is; mid confidence → body headings are preferred; low confidence → an empty map with the current fallback behavior (the escalation branch is wired by ticket 03).

**Blocked by:** None — can start immediately.

**Status:** done

- [x] Confidence score computed as the fraction of candidate titles that reappear in the body
- [x] Readable TOC (high confidence) wins over body headings; titles/pages unchanged
- [x] Mangled TOC (low confidence) recovers via body headings without dropping chapters on title drift
- [x] Low-confidence result yields an empty map and the current lesson fallback (no crash)
- [x] Golden fixtures (GOI, N3 Kanji) continue to extract the same maps

## Comments

Implemented 2026-08-14 (Phase 1, committed) in
`backend/src/services/curriculum_service.py`: `_cross_check_confidence()` +
`CONFIDENCE_HIGH=0.7` / `CONFIDENCE_LOW=0.3` gates; high→TOC, mid→body
headings, low→empty (now escalation, ticket 03). Tested in
`tests/unit/test_curriculum_service.py` (TestCrossCheck + title-drift and
readable-TOC-wins cases).
