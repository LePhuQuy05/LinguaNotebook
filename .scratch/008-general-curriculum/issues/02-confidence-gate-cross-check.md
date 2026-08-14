# 02 — Confidence gate + content-association cross-check

**What to build:** The rule scan measures how confident it is by checking whether candidate chapter titles from the TOC also reappear in the document's body. The cross-check is soft — no chapter is dropped because OCR made its title differ. High confidence → the TOC result is used as-is; mid confidence → body headings are preferred; low confidence → an empty map with the current fallback behavior (the escalation branch is wired by ticket 03).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Confidence score computed as the fraction of candidate titles that reappear in the body
- [ ] Readable TOC (high confidence) wins over body headings; titles/pages unchanged
- [ ] Mangled TOC (low confidence) recovers via body headings without dropping chapters on title drift
- [ ] Low-confidence result yields an empty map and the current lesson fallback (no crash)
- [ ] Golden fixtures (GOI, N3 Kanji) continue to extract the same maps

## Comments
