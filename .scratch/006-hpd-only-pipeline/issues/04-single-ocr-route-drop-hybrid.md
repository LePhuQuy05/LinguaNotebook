# 04 — Single OCR route — drop hybrid and Marker routing

**What to build:** Every upload takes one predictable path: PDFs with an embedded text layer use PyMuPDF extraction; scanned/image PDFs use HPD OCR. The "balanced" and "hybrid" branches (Marker first, then Qwen-VL re-parse of "important" pages) are removed from the parse routing — the 2026-08-01 parse proved hybrid is a silent no-op that doubles parse time with zero quality gain. The upload UI drops the mode selector (DPI and page-range controls stay). The API keeps accepting a `mode` parameter for backward compatibility, but the worker ignores it. The Qwen-VL integration module stays on disk, unwired, for Stage 2 reuse. `parse_method` always truthfully reports `text_layer` or `ocr`.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Parse routing has exactly two branches: text-layer → PyMuPDF, otherwise → HPD; no Marker/hybrid/Qwen-VL branches reachable
- [ ] Mode selector removed from the upload UI; page range and DPI controls unchanged
- [ ] API still accepts `mode` (ignored by the worker) — no frontend/API break
- [ ] Qwen-VL module remains in the repo, not imported by the parse path
- [ ] End-to-end verified: parse a scanned PDF and a text PDF → `parse_method` is `ocr` and `text_layer` respectively
- [ ] Parse timing predictable: scanned PDF ≈ 53s/page (HPD), no Qwen pages
