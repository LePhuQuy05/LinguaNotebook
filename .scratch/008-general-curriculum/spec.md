# 008 — General curriculum extraction (multi-language + optional SLM escalation)

**Status:** ready-for-agent

## Problem Statement

The curriculum extractor only understands Japanese textbook TOCs structured as `N課` (with a `N章` body-heading fallback added for the N3 Kanji book). Upload any other kind of document — a Korean, Chinese, or English textbook; a TOC without dotted page anchors; a document whose TOC the OCR mangled beyond the two known patterns — and the extractor returns an empty **curriculum map**, so daily lessons cannot be drawn chapter-by-chapter and the app silently falls back to random retrieval. There is no notion of how confident the rule scan is, and no way to recover a messy TOC short of hand-writing another regex.

## Solution

From the user's perspective: upload any textbook in a supported language (Japanese, Korean, Chinese, English/Latin) and the app builds a **curriculum map** of its own accord — no language setting required. When the rule scan cannot read the TOC confidently, an optional offline small-language model (if the self-hoster installed one) recovers the map; without it, the app degrades gracefully exactly as today.

## User Stories

1. As a user, I want a Korean textbook's map to be built automatically (부/장/과 markers), so that daily lessons work for Korean books without any setup.
2. As a user, I want a Chinese textbook's map to be built automatically (部/章/课/单元 markers), so that daily lessons work for Chinese books.
3. As a user, I want an English/Latin textbook's map to be built automatically (part/chapter/unit/lesson markers), so that daily lessons work for English books.
4. As a user, I want a book whose TOC uses plain numbered entries with no dotted page leaders (Ordered style) to still be mapped, so that a wide class of TOCs is covered.
5. As a user, I want a book whose TOC the OCR mangled to be recovered from its body headings when the **content-association cross-check** deems the TOC untrustworthy, so that the map is still built.
6. As a user, I want a document whose TOC and body headings both fail the rule scan to be recovered by the optional small-LM **escalation** when a model is installed, so that even messy documents get a map.
7. As a self-hoster, I want the app to work without any model download — when no model is present the escalation is skipped and behavior is identical to today, so that the offline-first install stays small.
8. As a user, I want a chapter that appears in both the TOC and the body to stay in the map even when OCR made the titles differ slightly, so that the cross-check never drops valid chapters.
9. As a user, I want a readable TOC to win over body headings (TOC source preferred), so that clean books keep their clean titles and pages.
10. As a user, I want daily lessons to keep working off the generalized map with no regression, so that the curriculum-driven lesson flow is preserved.
11. As a self-hoster, I want a documented one-line install of the small-LM runtime plus the model file path, so that enabling the escalation is a single documented step.
12. As a developer, I want the escalation path testable with a fake model adapter, so that the feature is unit-testable without shipping a model file in CI.
13. As a user, I want the escalation to never invent page numbers — every reported page must be a member of **Known pages** — so that lessons never cite a page that doesn't exist.
14. As a developer, I want the base install unchanged (no new required dependency), so that the escalation is strictly optional.

## Implementation Decisions

- **Structural-marker registry**: a language-agnostic merged set of structural markers, each tagged with a structural level (part/chapter/unit/lesson), covering Japanese, Korean, Chinese, and English/Latin. Detection never depends on knowing the document's language; the document's declared language, when set, selects only the practice-section stoplist used to skip non-chapter entries (e.g. まとめ/復習 vs Appendix/Index).
- **Confidence gate**: the rule scan computes a confidence score via the **content-association cross-check** — the fraction of candidate chapter titles that also reappear in the body. The gate is soft: no entry is dropped on mismatch alone. High confidence → the **TOC source** result is used as-is; mid confidence → the **body-heading source** is preferred; low confidence → **escalation**.
- **Escalation**: optional and offline. It runs inside the existing parse step (no new worker, no new document status) via a thread executor so the worker's persistent event loop is never blocked. It reads a model file from a configured path (`CURRICULUM_LLM_PATH`, gitignored model directory); an absent model skips escalation. It feeds only the isolated TOC pages plus **Known pages** to the model; output is grammar-constrained so every page number must be a member of Known pages; results are deterministically verified (parse → validate → whitelist membership → monotonic order → sequential numbering) before saving; page ranges are always computed in code, never by the model.
- **Dependency policy**: the small-LM runtime (`llama-cpp-python`) is an optional install documented for self-hosters, not a base requirement; the code imports it lazily and degrades gracefully when unavailable — matching the established precedent for the optional HPD OCR engine.
- **Documented default model**: Qwen3-1.7B Q4_K_M (Apache-2.0), configurable via the model path; Qwen3-4B documented as the accuracy option. Qwen2.5-3B / Qwen2.5-VL-3B are excluded (non-commercial license).

## Testing Decisions

- The primary seam is the existing pure extraction function (markdown → rows); it is extended per language with one fixture per language (JP/KO/ZH/EN), plus cases for the confidence gate's three branches, the soft cross-check (title drift does not drop a chapter), Ordered-style numbered TOCs, and the read-TOC-wins preference.
- The escalation is tested at the same seam via an injected fake model adapter that returns known rows; a real-model integration test is gated on the model file's presence and skipped when absent.
- Golden fixtures: the two known books (GOI 課-TOC and N3 Kanji 章-body) must continue to extract the same maps, unchanged.
- Coverage stays ≥80% (run `--no-cov` locally, per repo practice).
- Prior art: `tests/unit/test_curriculum_service.py` (existing seam + golden fixtures).

## Out of Scope

- VLM-based re-OCR of a garbled TOC page (noted in research as a possible future fallback; deferred).
- Auto-downloading the model (breaks the offline-first contract).
- GPU/iGPU acceleration (CPU-only by decision; the Arc iGPU is bandwidth-bound for ≤4B models).
- Language coverage beyond the four families (the registry is extensible by adding markers).
- Batch re-extraction of already-parsed documents (a one-off script can be written ad hoc).
- Changing the curriculum→lesson consumption flow (007 territory, already shipped).

## Further Notes

- Research: `docs/research/curriculum-extraction-generalization.md` (2026-08-14) — grounded the lexicon, model choice, constrained decoding, and runtime findings.
- ADR-0001 (rule-first extraction with optional SLM escalation; offline-first) and ADR-0002 (model choice: Qwen3-1.7B; reject Qwen2.5-3B non-commercial license and archived IPEX-LLM; CPU-only).
- Domain glossary: `CONTEXT.md` (Curriculum map, Chapter, Part, Structure source, Structural-marker registry, Content-association cross-check, Confidence gate, Escalation, Known pages).
