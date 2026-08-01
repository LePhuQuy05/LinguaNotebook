# 02 — Worker stores converted markdown + typed blocks

**What to build:** Documents parsed via OCR (fast/hybrid modes) display clean markdown in the app — no `<BLOCK>`, `<CHILD>`, or coordinate noise — and their content blocks are typed correctly (header, table, list...). The worker's block parser is replaced by the conversion service from ticket 01: the stored `content_markdown` comes from `convert_prediction_to_markdown`, and ContentBlock records come from `parse_blocks`. Degeneration deduplication still runs before conversion. Re-uploading a document applies the improved quality. Text-layer PDFs (PyMuPDF extraction) are unchanged.

**Blocked by:** 01 — HPD markdown conversion service.

**Status:** ready-for-agent

- [ ] Worker's block parser uses `parse_blocks()` instead of the hand-written regex; no block's content is dropped — headers, footers, page numbers, formulas all preserved
- [ ] Stored `content_markdown` is the converted clean markdown (no `<BLOCK>`/`<CHILD>`/bbox noise) in reading order
- [ ] Degeneration dedup (`_deduplicate_repeated_lines`) still runs before conversion — repeated-line collapse unchanged
- [ ] End-to-end verified: upload scanned PDF → parse → `GET` document → blocks typed correctly, content clean markdown
- [ ] Re-parse via re-upload yields the same clean quality
- [ ] Text-layer PDFs still use PyMuPDF extraction — output unchanged
- [ ] Regression: worker restart not needed after redeploy of the parser change is documented (or the worker is restarted as part of verification)
