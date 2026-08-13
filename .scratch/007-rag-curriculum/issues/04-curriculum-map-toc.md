# 04 — Curriculum map from the book's table of contents

**What to build:** Japanese textbooks are chapter-structured (Shinkanzen N3: 第1部 話題別 / 第2部 性質別 with chapter topics like 人・体, 天気, 学校…, each with page numbers) and the TOC lives in the book's front matter — pages ~4–6 of the OCR'd markdown. A rule-based extractor reads the TOC pages, matches 第N部 / 第N章 patterns, resolves each chapter's page range from the `--- Page N ---` markers, and stores rows in a new `DocumentStructure` table. No LLM. Conservative by design: unknown structure → no map (lessons fall back to current behavior).

**Blocked by:** 01 (clean markdown before structure extraction)

**Status:** ready-for-agent

- [ ] New `DocumentStructure` model: document_id, part, chapter, topic, page_start, page_end, order
- [ ] Extractor service: takes the parsed markdown, finds the TOC pages, emits structure rows for the real GOI.pdf (golden fixture — 第1部/第2部 chapters with page ranges)
- [ ] Page ranges resolved from `--- Page N ---` markers, never array indexes
- [ ] Unknown/absent TOC patterns → empty map, no crash
- [ ] Unit tests with a synthetic TOC + golden-fixture test on the real book

## Comments

2026-08-13 — Implemented + committed (03aa5b2): rule-based extractor
(第N部 part headers, `N課<topic>` entries with dotted page numbers, practice
sections 実力を試そう/第N回/模擬 bridged). Verified against real GOI.pdf:
29 chapters, weather chapter at page 76. OCR merge case "32課 第2部 …" treated
as a part boundary. Conservative: no match → empty map.
