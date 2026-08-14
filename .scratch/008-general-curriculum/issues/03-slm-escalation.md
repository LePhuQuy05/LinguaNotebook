# 03 — Optional SLM escalation + deterministic verification

**What to build:** When the rule scan's confidence is below the gate and a model file is present, the extractor calls an offline small-language model to recover the curriculum map from the isolated TOC pages plus the document's Known pages. The model's page numbers are grammar-constrained to Known pages (it cannot invent one); results are deterministically verified before saving; page ranges are computed in code. When no model is present, escalation is skipped and behavior is unchanged.

**Blocked by:** 02 — the gate's low-confidence branch triggers this.

**Status:** ready-for-agent

- [ ] Escalation triggers only below the low-confidence threshold
- [ ] Only the isolated TOC pages + Known pages are sent to the model (not the whole book)
- [ ] Page numbers are constrained to Known pages; a hallucinated page is impossible
- [ ] Output verified: parse → validate → whitelist membership → monotonic order → sequential numbering; page ranges computed in code
- [ ] Escalation runs inside the parse step without blocking the worker's persistent event loop
- [ ] No model present → escalation skipped, behavior identical to today
- [ ] Tested with a fake model adapter; real-model integration test gated on the model file

## Comments
