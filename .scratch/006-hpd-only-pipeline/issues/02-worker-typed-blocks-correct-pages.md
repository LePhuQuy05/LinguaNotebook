# 02 — Worker stores typed blocks with correct page numbers

**What to build:** The document viewer stops showing one giant "paragraph" per page with shifted page numbers. The worker's block-saving path uses the parser service from ticket 01 instead of the current regex fallback, and page numbers come from the actual `--- Page N ---` markers in the combined markdown — not from array indexes. A 5-page PDF stores blocks labeled Page 1–5 (today it stores 2–6). `total_pages` reflects the highest parsed page number. Re-uploading a document produces the same improved quality.

**Blocked by:** 01 — Markdown block parser service.

**Status:** ready-for-agent

- [ ] Worker's block-saving logic calls the parser service per page; every page yields multiple typed blocks (header/table/list/paragraph) instead of one fallback paragraph
- [ ] Page numbers extracted from the `--- Page N ---` markers; a 5-page PDF produces blocks numbered 1–5 (regression: today it produces 2–6)
- [ ] `total_pages` equals the highest parsed page number
- [ ] `_deduplicate_repeated_lines` still runs before block parsing — degeneration collapse unchanged
- [ ] End-to-end verified: upload scanned PDF → parse → fetch document → blocks typed correctly, page numbers correct, no tag or coordinate noise in content
- [ ] Re-parse via re-upload yields the same clean quality
- [ ] Worker restarted after deployment; "Model Path:" startup log confirms new code is loaded
