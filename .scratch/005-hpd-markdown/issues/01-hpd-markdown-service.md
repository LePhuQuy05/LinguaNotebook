# 01 — HPD markdown conversion service

**What to build:** A reusable service that converts raw HPD `<BLOCK>/<CHILD>` prediction output into (a) clean per-page markdown with no tag noise and correct reading order, and (b) a list of typed blocks (category, bbox, content) so the worker can store proper ContentBlock records. Formula blocks get LaTeX normalization (`≈` → `\approx`, `×` → `\times`). The conversion logic is adapted from the HPD model repo's own conversion tool (`eval/hpd_to_markdown.py`), with attribution — the project's current hand-written regex is a lossy subset of it.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Service exposes `convert_prediction_to_markdown(pred: str) -> str` — given a raw `<BLOCK>/<CHILD>` stream, returns clean markdown: no `<BLOCK>`, `<CHILD>`, or `[x1,y1,x2,y2]` noise; text in reading order; chart/seal blocks dropped; formula tails cleaned; Unicode arithmetic operators normalized to LaTeX
- [ ] Service exposes `parse_blocks(pred: str) -> list[Block]` — each Block carries category, bbox, and content; header/title → header, paragraph/text → paragraph, table → table, list → list, image_caption → image_caption, everything else (footer, page_number, formula, unknown) → paragraph with content preserved
- [ ] Both functions handle per-page input (one page's prediction at a time), so the worker can convert page-by-page
- [ ] A golden fixture: one real HPD prediction page captured from an actual parse (e.g. Shinkanzen N3), stored in the test suite, with expected markdown asserted
- [ ] Unit tests cover: tag-stripping + reading order, typed block extraction with correct types + bboxes, LaTeX normalization, and a page with a table block
- [ ] Verify a real captured prediction (via CLI invocation) produces clean markdown — no tag noise, table renders as a markdown table
