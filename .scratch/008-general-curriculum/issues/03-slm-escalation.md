# 03 — Optional SLM escalation + deterministic verification

**What to build:** When the rule scan's confidence is below the gate and a model file is present, the extractor calls an offline small-language model to recover the curriculum map from the isolated TOC pages plus the document's Known pages. The model's page numbers are grammar-constrained to Known pages (it cannot invent one); results are deterministically verified before saving; page ranges are computed in code. When no model is present, escalation is skipped and behavior is unchanged.

**Blocked by:** 02 — the gate's low-confidence branch triggers this.

**Status:** done

- [x] Escalation triggers only below the low-confidence threshold
- [x] Only the isolated TOC pages + Known pages are sent to the model (not the whole book)
- [x] Page numbers are constrained to Known pages; a hallucinated page is impossible
- [x] Output verified: parse → validate → whitelist membership → monotonic order → sequential numbering; page ranges computed in code
- [x] Escalation runs inside the parse step without blocking the worker's persistent event loop
- [x] No model present → escalation skipped, behavior identical to today
- [x] Tested with a fake model adapter; real-model integration test gated on the model file

## Comments

Implemented 2026-08-14 in `backend/src/services/curriculum_escalation.py`
(`_build_prompt` / `_verify_and_finalize` / `build_curriculum_escalator`, lazy
`llama-cpp-python` adapter cached per process) and wired into
`extract_curriculum(markdown, language=None, escalator=None)` in
`curriculum_service.py` (low-confidence branch, `elif` so recovery feeds the
shared range computation) and `parse_worker.py::_save_curriculum_structure`
(`build_curriculum_escalator()` + `loop.run_in_executor`). Tests:
`tests/unit/test_curriculum_escalation.py` (12 unit + 1 model-gated) and
`TestEscalation` in `test_curriculum_service.py` (5). All 20 Phase-2 tests
green; full unit suite with the 80% coverage gate green.

Code-review pass (2026-08-14) applied four fixes:
1. **Immutability (HARD):** `_verify_and_finalize` renumbered rows by mutating
   `entry["chapter_num"]` in place — now builds `(title, page)` pairs and
   constructs the final `Entry` dicts in one comprehension, never mutating.
2. **Both-fail trigger (spec user story 6):** escalation now also fires when
   the TOC scan found chapter-looking lines but every dotted anchor was
   mangled (`toc_entries` empty yet `toc_pages` non-empty) and both body
   fallbacks return nothing — the model still reads the real TOC pages.
3. **Stoplist parity:** recovered entries are filtered through the same
   practice-section stoplist as rule-scan output (`_drop_stoplist`), so a
   model emitting まとめ/実力を試そう/Appendix cannot mint a chapter row.
4. **Clean diff:** reverted the `ruff format` reflow of pre-existing files;
   adapter knobs (`_CTX`/`_THREADS`/`_MAX_TOKENS`/`_STOP_SEQ`) promoted to
   named constants; llama-cpp return normalized through `str()` for `--strict`.
Module coverage: `curriculum_escalation.py` 81%, `curriculum_service.py`
98% (missed lines are the model-gated paths, by design).
