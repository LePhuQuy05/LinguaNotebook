# 01 — Markdown block parser service

**What to build:** A reusable service that converts one page of HPD's markdown output into a list of typed blocks. HPD already emits plain markdown (pipe tables, heading-like lines, list markers) — the parser recognizes what's actually there: consecutive `| ... |` lines (including `| --- |` separators) become one `table` block with the markdown table text intact; standalone short heading-like lines (e.g. はじめに, ■本書の特徴, lines ending in `：`) become `header`; lines starting with list markers (`・`, `-`, `*`, `1.`, `①`) become `list`; everything else becomes `paragraph`. Blocks come back in reading order. The service is verified against the real Shinkanzen N3 parse output (document `00f26d1a-ac6f-4528-8a39-44266df520b5`, already in storage) as a golden fixture.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Service exposes `parse_page_blocks(page_text: str) -> list[Block]`; `Block` carries `block_type`, `bbox` (None for markdown-mode output), and `content` (clean markdown text)
- [ ] Mixed input (heading + table + list + paragraph in one page) returns ≥4 blocks in reading order with correct types
- [ ] Pipe table with `| --- |` separator rows collapses into a single `table` block, markdown table text preserved verbatim
- [ ] Golden fixture test: the real Shinkanzen N3 TOC page (from the 2026-08-01 parse) produces multiple typed blocks — no single giant paragraph, tables survive
- [ ] Classification is conservative: misclassifying a heading as a paragraph is acceptable, but table rows must never split into separate blocks
- [ ] CLI/demo invocation against the golden fixture output shows typed blocks — runnable standalone without the app
