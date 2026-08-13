# 01 — Clean OCR markup noise from blocks

**What to build:** OCR'd markdown sometimes contains HTML the pipeline shouldn't keep — measured on GOI.pdf: 75 blocks with dead `<img src="imgs/...">` references (images are never downloaded) and 88 `<div style="...">` wrappers. These tags become junk tokens inside vector embeddings and dilute every retrieval. A `clean_markdown()` function strips HTML tags from the markdown while leaving Japanese text (and legitimate `<`/`>` math/symbols) intact, and the worker applies it before storing — so both the Postgres blocks and the MinIO `combined.md` are clean at the source.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `clean_markdown(text)` removes `<img …>`, `<div …>`/`</div>`, and other HTML tags; keeps surrounding text and line structure
- [ ] Japanese text, furigana lines, and markdown tables pass through untouched
- [ ] Symbolic `<`/`>` usage (e.g. `A < B`, `A<B`) survives — the regex must not eat math or comparison operators
- [ ] Worker applies cleaning to the combined markdown once, before MinIO upload and block saving (both artifacts clean)
- [ ] Unit tests cover: tag stripping, Japanese preservation, math-symbol survival, tag-only strings → empty
- [ ] Re-parse/clean a real document and verify zero `<img`/`<div` remain in blocks and `combined.md`

## Comments

2026-08-11 — Implemented + committed (87dafd5). Verified against real GOI.pdf
output (doc 16116abe): `<img` 75→0, `<div` 88→0, page markers 186 intact,
Japanese preserved (416,243 → 151,656 chars — 264 KB was inline tag/base64
junk). Code-review two-axis passed; regex tightened per finding
(`<div>foo > bar</div>` keeps "foo > bar"). 82 unit tests green.
