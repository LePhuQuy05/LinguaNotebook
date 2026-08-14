# 01 — Multi-language structural-marker registry

**What to build:** The curriculum extractor finds chapters in Korean, Chinese, and English/Latin textbooks on its own — no language setting needed. A merged, language-agnostic registry of structural markers (each tagged with a level: part/chapter/unit/lesson) drives detection; the document's declared language, when set, only selects the practice-section stoplist (まとめ/復習 vs Appendix/Index). Ordered-style TOCs (number-prefixed entries, no dot leaders) are handled too. Japanese books keep extracting exactly as today.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] A Korean textbook TOC (부/장/과 markers) produces a curriculum map
- [ ] A Chinese textbook TOC (部/章/课/单元) produces a curriculum map
- [ ] An English/Latin textbook TOC (part/chapter/unit/lesson) produces a curriculum map
- [ ] A numbered TOC without dot leaders (Ordered style) produces a map
- [ ] The practice-section stoplist differs by declared language; non-chapter entries are skipped
- [ ] Existing Japanese extraction (GOI 課-TOC, N3 Kanji 章-body golden fixtures) is unchanged
- [ ] One unit test fixture per language

## Comments
