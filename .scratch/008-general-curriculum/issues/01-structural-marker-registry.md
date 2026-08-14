# 01 — Multi-language structural-marker registry

**What to build:** The curriculum extractor finds chapters in Korean, Chinese, and English/Latin textbooks on its own — no language setting needed. A merged, language-agnostic registry of structural markers (each tagged with a level: part/chapter/unit/lesson) drives detection; the document's declared language, when set, only selects the practice-section stoplist (まとめ/復習 vs Appendix/Index). Ordered-style TOCs (number-prefixed entries, no dot leaders) are handled too. Japanese books keep extracting exactly as today.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] A Korean textbook TOC (부/장/과 markers) produces a curriculum map
- [x] A Chinese textbook TOC (部/章/课/单元) produces a curriculum map
- [x] An English/Latin textbook TOC (part/chapter/unit/lesson) produces a curriculum map
- [x] A numbered TOC without dot leaders (Ordered style) produces a map
- [x] The practice-section stoplist differs by declared language; non-chapter entries are skipped
- [x] Existing Japanese extraction (GOI 課-TOC, N3 Kanji 章-body golden fixtures) is unchanged
- [x] One unit test fixture per language

## Comments

Implemented 2026-08-14 (Phase 1, committed) in
`backend/src/services/curriculum_service.py`: merged `_MARKERS` registry
(部/부/Part, 章/장/Chapter, 単元/단원/单元/Unit, 課/课/과/Lesson), language-scoped
`_stoplist()`, `_NUM_PREFIX_RE` ordered-style TOC, body-heading and numbered-
section workbook fallbacks. Tested in `tests/unit/test_curriculum_service.py`
(TestKorean/TestChinese/TestEnglish/TestOrderedStyle/TestBodyHeadings/etc.).
