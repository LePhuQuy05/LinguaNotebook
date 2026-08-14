# Curriculum Extraction: Generalizing Beyond Japanese TOCs — 2026-08-14

Assessment of how to generalize the current rule-based curriculum extractor
(`backend/src/services/curriculum_service.py`) beyond Japanese `N課`/`N章`
textbook TOCs to arbitrary languages and document types — without and, where
worth it, with a small local LLM. Grounded in the current code, the app's
offline/CPU/iGPU constraint (Intel Arc 140V + CPU, BGE-M3 on CPU), and primary
sources verified during this research.

## Tóm tắt (Summary)

- **Rule-based path generalizes well and cheaply.** The current two-pass design
  (TOC dotted-anchor scan → body-heading fallback) already embodies the two
  standard non-LLM techniques (TOC-page detection + heading hierarchy). The
  cheapest, highest-leverage upgrade is a **per-language structural-marker
  lexicon** (JP 部/章/課/単元, KO 부/장/과/단원, ZH 部/章/课/单元, EN
  part/chapter/unit/lesson) + a **content-association cross-check** (verify a
  TOC candidate heading actually reappears in the body). No new dependency
  needed.
- **Heavy PDF→markdown libraries are a poor fit here.** GROBID, MinerU, Marker,
  Nougat accept PDF/image only (our input is already OCR'd markdown); Nougat
  (CC-BY-NC) and Marker (commercial-restricted weights) block an MIT app;
  MinerU deletes page numbers. **Docling** (MIT) is the only one that accepts
  markdown input and emits a heading tree — but it won't parse our
  `--- Page N ---` markers into a curriculum table.
- **A small text-only LLM is viable as an *escalation fallback*, not the
  default.** Best fit for this project: **Qwen3-4B Q4_K_M in non-thinking mode
  (Apache-2.0)**, or **Qwen3-1.7B** for CPU speed. **Avoid Qwen2.5-3B and
  Qwen2.5-VL-3B — both are under the Qwen Research non-commercial license.**
  A VLM is unnecessary when we already have OCR text; text-only is strictly
  better here.
- **Constrained decoding (grammar) is mandatory** for small models — but the
  "constraint tax" paper shows hard schemas can *lower* answer accuracy even
  while raising schema validity. Pattern: **reason free, constrain late** —
  constrain page numbers tightly (they're grounded facts, whitelist from the
  observed page set), keep titles free-form, cross-check with a rule scan.
- **Runtime: `llama-cpp-python` (MIT), CPU-only.** The Arc 140V iGPU is
  bandwidth-bound and adds oneAPI/Vulkan complexity for at most ~1.5–2× over a
  modern CPU at Q4. **IPEX-LLM (Intel's Arc LLM path) was archived Jan 2026 —
  do not build on it.**

---

## 1. Generalizing the rule-based path — kỹ thuật không cần LLM

The current extractor already implements three of the standard non-LLM signals
for Japanese only: part headers (`第(\d+)部`), chapter entries (`N[課课]`), dotted
page anchors, plus a `## N章` body-heading fallback. Generalizing means
(1) broadening the *techniques*, (2) broadening the *lexicon*, and (3) knowing
which libraries already do this well.

### 1.1 Heading-hierarchy detection

Three non-LLM signals, all verified:

1. **Markdown heading level** (already in this repo): the HPD pipeline emits
   `## N章` headings, and `_BODY_CHAPTER_RE` already parses `#`/`##`/`###`. This
   is the highest-value signal and costs nothing.
2. **PDF font size/weight** (only if we ever re-process raw PDFs): PyMuPDF
   `page.get_text("dict")` exposes per-span `size` + bold flags; the standard
   algorithm classifies headings as spans ≥ ~1.4× the modal body size and/or
   bold, mapping the top-N distinct sizes to H1/H2/H3. PyMuPDF also has
   `doc.get_toc()`, which reads the PDF's **embedded outline** (`[level, title,
   page]`) — the authoritative hierarchy when present. The companion lib
   PyMuPDF4LLM ships `TocHeaders`/`IdentifyHeaders` that encapsulate this
   inference. pdfminer.six exposes per-char `size`/`fontname` but does no
   heading detection itself. pdfplumber exposes `fontname`/`size` per char but
   likewise no detection.
   - [PyMuPDF Document docs — `get_toc`](https://pymupdf.readthedocs.io/en/latest/document.html)
   - [PyMuPDF4LLM API — `TocHeaders`](https://docs.pdf4llm.com/python/api/tocheaders)
   - [pdfminer.six README](https://github.com/pdfminer/pdfminer.six)
   - [pdfplumber README](https://github.com/jsvine/pdfplumber)
3. **Numbering patterns** (language-independent, cheap): ordinal regexes like
   `^\d+(\.\d+)*$`, `Chapter\s+\d+`, `第\d+課`; full-width digit normalization
   (`０１２３…→0-9`) is already in `_FULLWIDTH_DIGITS`. The IEEE TOC paper below
   relies on ordinal sequences ("1.2", "1.2.1") as a primary discriminator.

### 1.2 Universal TOC-page detection

The recurring, verified signals across the literature and implementations:
(1) many short lines ending in page numbers, (2) dot leaders (`......` — or
`. . . .` as PDF text extraction often renders them), (3) right-aligned trailing
page numbers at a consistent x-position, (4) shared left margin / consistent
line geometry, (5) bounded by a Contents heading and an Index entry.

Verified references:

- **pdf_oxide `TocDetector`** (Rust crate, MIT/Apache-2.0): checks the `/TOC`
  structure tree first, then falls back to "geometric pattern detection (dot
  leaders, right-aligned page numbers)". Config knobs: `min_dot_leader_length`
  (default 3), `min_entries_for_confidence` (3), `confidence_threshold` (0.5).
  - [docs.rs TocDetector](https://docs.rs/pdf_oxide/latest/pdf_oxide/pipeline/converters/toc_detector/index.html)
  - [struct TocDetector](https://docs.rs/pdf_oxide/latest/pdf_oxide/pipeline/converters/toc_detector/struct.TocDetector.html)
- **`toc_regex_extractor.py`** — an open-source deterministic TOC extractor
  that finds the `Table of Contents` heading and the `Index` end-marker,
  reassembles multi-line entries, and parses them with dot-leader / spaces /
  page-only / `Chapter \d+` patterns. This is the closest open-source template
  to what `curriculum_service.py` already does.
  - [toc_regex_extractor.py](https://github.com/krugoll/Semantic-chunking-pipeline-for-RAG-from-scratch/blob/main/toc_regex_extractor.py)
- **IEEE "Table of contents recognition and extraction for heterogeneous book
  documents"** — catalogues why single heuristics fail and proposes adaptive
  rule selection over three TOC styles: **Flat** (parse sequentially),
  **Ordered** (entries carry section numbers → parse by number order),
  **Divided** (visual blocks → hierarchy via blocks).
  - [IEEE Xplore 6628805](https://ieeexplore.ieee.org/document/6628805/authors)
- **Lin & Xiong, "Detection and analysis of table of contents based on content
  association"** — the strongest *training-free* approach: pick candidate TOC
  pages (first ~20), then associate TOC entries with body pages by matching
  titles/page numbers, scoring each candidate page. **This is the 
  content-association cross-check** — the highest-leverage robustness upgrade
  for this project.
  - [DOI 10.1007/s10032-005-0149-4](https://doi.org/10.1007/s10032-005-0149-4)

**Bottom line:** our `_PAGE_DOTS_RE` is already the dot-leader detector. The
generalizable upgrade is (a) bounding the TOC region with Contents/Index
markers, (b) the **content-association cross-check** (a TOC candidate heading
must reappear in the body within the claimed page range — this survives OCR
mangling of the dotted leaders), and (c) the Flat/Ordered/Divided style
distinction so a TOC without dot leaders (number-prefixed entries) is handled
instead of falling through to the body-heading fallback.

### 1.3 Cross-language structural-marker lexicons

No single comprehensive open-source gazetteer of document-structure markers
exists (searched extensively); but the markers are a small closed set per
language, and each entry below was verified against real code or textbook data:

| Language | Part | Chapter | Unit | Lesson | Section | Practice/mock |
|---|---|---|---|---|---|---|
| Japanese | 部 | 章 | 単元 | 課 | 節 | 回, 第N回 |
| Korean | 부 | 장 | 단원 | 과 | 절 | 회 |
| Chinese (simp) | 部 | 章 | 单元 | 课 | 节 | 回 |
| English/Latin | Part | Chapter | Unit | Lesson | Section | Appendix, Preface, Index |

Verified sources:
- Japanese in the project itself: `_PART_RE` (部), `_CHAPTER_RE` (課/课),
  `_BODY_CHAPTER_RE` (課/章). Independent confirmation of 単元 as a textbook
  unit marker in open-source notes:
  [xinwu-yang/nippon](https://github.com/xinwu-yang/nippon) (`# ５単元`).
- Korean: the `hyunwoongko/kss` spacing library ships a structural-unit wordlist
  including `단원|장|절`:
  [kss spacing/utils.py](https://github.com/hyunwoongko/kss/blob/master/kss/_modules/spacing/utils.py);
  the `nc2U/ibs` Korean textbook model uses fields named `단원 명칭` (unit name)
  and `단원 레벨`:
  [nc2U/ibs models.py](https://github.com/nc2U/ibs/blob/master/app/django/book/models.py).
- English/Latin: `_CHAPTER_ONLY` (`Chapter \d+`, `Appendix [A-Z]`) and
  `_CONTENTS_HEADING` (`Table of Contents`/`Contents`) in
  [toc_regex_extractor.py](https://github.com/krugoll/Semantic-chunking-pipeline-for-RAG-from-scratch/blob/main/toc_regex_extractor.py).
- Chinese: the existing `_CHAPTER_RE` already accepts both 課 and 课; the
  simplified set (章/节/单元/部) is the same closed family.

**Recommendation:** don't hunt for a library — encode a per-language
`dict[str, tuple[str, ...]]` (marker → level) and match both the marker and its
position in a heading/numbering pattern. This is ~30 lines of extension to the
current code.

### 1.4 Library comparison (verified against official READMEs/docs)

| Library | Offline? | GPU needed? | Hierarchical output? | Input format | License |
|---|---|---|---|---|---|
| **GROBID** | Yes | No (CRF, CPU default) | Yes — TEI/XML with section titles, PDF coords | **PDF only** | Apache-2.0 |
| **IBM Docling** | Yes (models cached after first run) | No (CPU via ONNX) | **Yes** — `DoclingDocument` heading tree, per-item page `prov` | **Markdown**, PDF, DOCX, HTML, images, EPUB | MIT |
| **MinerU** | Yes | Optional (CPU backend slow; GPU rec.) | Partial — preserves headings; **deletes page numbers** | PDF/DOCX/PPTX/images | Custom (Apache-based, extra conditions) |
| **Marker (marker-pdf)** | Mostly (local models; `--use_llm` is online) | No (CPU/GPU/MPS) | Yes — JSON `section_hierarchy` + `table_of_contents` | PDF/images/DOCX/HTML | Code Apache-2.0; **weights commercial-restricted** |
| **Unstructured.io** | Yes | No (tesseract/poppler; `hi_res` optional) | Partial — flat element list, no page-numbered TOC | PDF, HTML, text, docx, ... | Apache-2.0 |
| **Nougat** | Yes (weights downloaded once) | No, but CPU slow (GPU-oriented) | **No** — flat Mathpix markdown per page | **PDF only** | Code MIT; **weights CC-BY-NC (non-commercial)** |
| **PyMuPDF** | Yes | No | `doc.get_toc()` reads embedded outline `[level,title,page]` | PDF | AGPL-3.0 / commercial dual |
| **pdfminer.six** | Yes | No | No detection; exposes char size/fontname | PDF | MIT |
| **pdfplumber** | Yes | No | `pdf.toc` (embedded outline) only | PDF | MIT |

Source URLs:
- GROBID: [README](https://github.com/kermitt2/grobid) — Apache-2.0, CPU default, Java (Linux/macOS; Windows unsupported).
- Docling: [README](https://github.com/docling-project/docling) — MIT, air-gapped; [supported formats](https://docling-project.github.io/docling/usage/supported_formats/) (`.md` → `MarkdownDocumentBackend`); [ONNX models on CPU](https://github.com/docling-project/docling/blob/11a1bb5d/docs/usage/vision_models.md).
- MinerU: [README](https://github.com/opendatalab/MinerU) — custom license; "Remove … page numbers"; CPU `-b pipeline` backend.
- Marker: [README](https://github.com/datalab-to/marker) — code Apache-2.0, weights "modified AI Pubs Open Rail-M"; JSON `section_hierarchy` + `table_of_contents`.
- Unstructured: [README](https://github.com/Unstructured-IO/unstructured) — Apache-2.0.
- Nougat: [README](https://github.com/facebookresearch/nougat) — code MIT, weights CC-BY-NC; `--full-precision` CPU note.
- PyMuPDF: [about/license](https://pymupdf.readthedocs.io/en/latest/about.html); [`get_toc`](https://pymupdf.readthedocs.io/en/latest/document.html).
- pdfminer.six: [README](https://github.com/pdfminer/pdfminer.six); pdfplumber: [README](https://github.com/jsvine/pdfplumber).

### 1.5 Verdict

**None of the heavy PDF→markdown libraries fit this pipeline.** Reasons:
input mismatch (only Docling/Unstructured accept text, and our input is already
markdown); license blockers for an MIT app (Nougat CC-BY-NC, Marker weights,
MinerU custom license, PyMuPDF AGPL); and they don't produce what we need
(MinerU deletes page numbers; Unstructured is flat; Nougat is per-page flat
markdown). **Docling** is the one worth a second look — MIT, CPU/offline, accepts
`.md`, emits a heading tree — but it won't parse our `--- Page N ---` markers
into a curriculum table, so it adds a large dependency tree for a job the regex
already does.

**Recommended non-LLM path (no new dependencies):** keep the two-pass design;
generalize the lexicon (1.3); add the content-association cross-check (1.2);
adopt Flat/Ordered/Divided style detection. Optionally, if ever re-processing
raw PDFs, use `PyMuPDF.get_toc()` for a free embedded-outline check.

---

## 2. Small-language-model curriculum extraction — mô hình nhỏ chạy offline

Bottom line: the clear winner for this use case is **Qwen3-4B Q4_K_M in
non-thinking mode** (Apache-2.0, native tool/JSON support, excellent CJK,
~2.6 GB at Q4 — fits the Arc 140V's ~8 GB shared VRAM, still acceptable on CPU).
Two critical flags: **Qwen2.5-3B and Qwen2.5-VL-3B are under the Qwen Research
non-commercial license** (verified the LICENSE file) — do not use them in a
commercial app. For TOC extraction over already-OCR'd markdown, a **text-only
LLM is the right tool**; a VLM is unnecessary and strictly worse.

### 2.1 Comparison table (verified against HF model cards / official releases)

Columns: model · params · Q4_K_M RAM (approx) · JSON/structured output · CPU
tok/s (measured where found) · license · CJK

| Model | Params | Q4 RAM | JSON/structured | CPU tok/s | License | CJK |
|---|---|---|---|---|---|---|
| Qwen3-4B (non-thinking) | 4.0B | ~2.6 GB | Native tool calling + JSON; use non-thinking | ~7–12 desktop CPU | Apache-2.0 ✅ | Excellent |
| Qwen3-1.7B | 1.7B | ~1.3 GB | Tool calling + JSON | ~25–50 est. | Apache-2.0 ✅ | Excellent |
| Qwen3-0.6B | 0.6B | ~0.5 GB | Tool calling (thinking off) | ~50–100 est. | Apache-2.0 ✅ | Excellent |
| Qwen3-8B | 8B | ~5.5 GB | Tool calling + JSON | ~5–10 CPU | Apache-2.0 ✅ | Excellent |
| Qwen2.5-7B | 7B | ~4.9 GB | JSON mode; strong tool use | ~10–15 | Apache-2.0 ✅ | Excellent |
| Qwen2.5-3B | 3.09B | ~2.0 GB | JSON mode | ~15–30 est. | **Qwen Research — NON-COMMERCIAL ❌** | Excellent |
| Phi-4-mini | 3.8B | ~2.5 GB | **Native tool-calling + `structured_outputs: true`** (best 4B) | ~7–15 CPU | MIT ✅ | Weak but usable |
| Phi-3.5-mini | 3.8B | ~2.5 GB | JSON via grammar only | ~8–15 | MIT ✅ | Weak |
| Gemma 3 4B | 4B | ~2.6 GB | Tool calling unreliable at 4B → grammar needed | ~8–12 desktop CPU | Gemma Terms (custom) ⚠️ | Good (140+ langs, CJK tokenizer) |
| Gemma 3 1B | 1B | ~0.8 GB | Function calling not reliable → grammar | ~30–60 est. | Gemma Terms ⚠️ | Weak (text-only, EN-heavy) |
| Llama 3.2 3B | 3.21B | ~2.2 GB | Tool calling unreliable (0–9/10 measured) → grammar | ~28–72 | Llama Community ⚠️ | **None (8 langs, no CJK)** |
| Llama 3.2 1B | 1.2B | ~0.9 GB | Tool calling unreliable → grammar | ~30–60 est. | Llama Community ⚠️ | **None** |
| SmolLM2-1.7B | 1.7B | ~1.1 GB | Tool calling weak (BFCL 27%) → grammar | ~30–50 est. | Apache-2.0 ✅ | **None (EN-only)** |
| SmolLM3-3B | 3B | ~2.0 GB | Tool calling (xml/python) → grammar | ~10–25 est. | Apache-2.0 ✅ | **None (6 langs)** |
| Qwen2.5-VL-3B | ~3.75B | ~3 GB + vision | JSON via grammar; VLM slower | slower than text | **Qwen Research — NON-COMMERCIAL ❌** | Excellent (Doc VQA) |
| Qwen2.5-VL-7B | ~8.3B | ~6 GB + vision | JSON via grammar | slow on CPU | Apache-2.0 ✅ | Excellent |
| GOT-OCR2.0 | 0.58B | ~0.6 GB | OCR→text only, not structured JSON | fast (tiny) | Apache-2.0 ✅ | Good (CN/EN OCR) |

### 2.2 Key verified facts per family

- **Qwen2.5:** 0.5B/1.5B/7B = Apache-2.0; **3B = `qwen-research`**, the LICENSE
  file states "FOR NON-COMMERCIAL PURPOSES ONLY… If you are commercially using
  the Materials, you shall request a license from us."
  - [HF API record](https://huggingface.co/api/models/Qwen/Qwen2.5-3B-Instruct),
    [Qwen2.5-3B LICENSE](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/raw/main/LICENSE),
    [Qwen2.5-7B card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct). 32K native
    context; model card lists "generating structured outputs especially JSON".
- **Qwen3:** all sizes Apache-2.0 ([HF API Qwen3-8B](https://huggingface.co/api/models/Qwen/Qwen3-8B)).
  4B/8B = 128K via YaRN. **Thinking is on by default** and wraps output in
  `<think>…</think>` — set `enable_thinking=False` (or `/no_think`) for
  extraction. There are known vLLM/SGLang grammar bugs when thinking is
  disabled; the documented path is `response_format=json_schema` +
  `enable_thinking=False`. ([Qwen3-4B card](https://huggingface.co/Qwen/Qwen3-4B),
  [vLLM issue #18819](https://github.com/vllm-project/vllm/issues/18819),
  [SGLang issue #6675](https://github.com/sgl-project/sglang/issues/6675))
- **Phi-4-mini:** MIT, 128K context, and the standout structured-output model —
  native tool tokens + `structured_outputs: true`; Phi-3/3.5 lack native tool
  tokens. Weak CJK (English-dominant).
  ([Phi-4-mini card](https://huggingface.co/microsoft/Phi-4-mini-instruct),
  [Phi-4-mini GGUF README](https://huggingface.co/Mungert/Phi-4-mini-instruct.gguf/blob/main/README.md))
- **Llama 3.2:** commercial use allowed (with "Built with Llama" attribution,
  naming, and a 700M-MAU threshold) but **not OSI**; **officially no
  CJK support**; tool calling empirically unreliable (0/10–5/10 without a
  literal JSON skeleton). ([Llama 3.2 LICENSE](https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/LICENSE),
  [Escapement small-model study](https://github.com/fulcrologic/escapement/blob/main/docs/structured-output-from-small-models.md))
- **Gemma 3:** custom Gemma Terms of Use (commercial use permitted/fee-free but
  not OSI, with redistribution obligations + prohibited-use policy) — legal
  review recommended; 4B = multimodal, 128K, 140+ langs with CJK-optimized
  tokenizer; 1B = text-only/EN-heavy. Tool calling unreliable at 4B → grammar.
  ([Gemma Terms](https://ai.google.dev/gemma/terms),
  [Gemma 3 model card](https://ai.google.dev/gemma/docs/core/model_card_3),
  [Gemma3 Ollama tools testing](https://github.com/IllFil/gemma3-ollama-tools))
- **SmolLM2/SmolLM3:** Apache-2.0; SmolLM2 is English-only, SmolLM3 supports only
  EN/FR/ES/DE/IT/PT — **neither handles CJK**.
  ([SmolLM2 card](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct),
  [SmolLM3 blog](https://huggingface.co/blog/smollm3))
- **VLMs:** Qwen2.5-VL-3B is non-commercial (verified
  [LICENSE](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/raw/main/LICENSE));
  Qwen2.5-VL-7B Apache but 6 GB+ and slow on CPU. GOT-OCR2 (0.58B, Apache) is a
  lightweight image→text fallback but not a structured extractor.
  ([GOT-OCR2_0](https://huggingface.co/stepfun-ai/GOT-OCR2_0))

### 2.3 Text-only LLM vs VLM

The pipeline already produces `--- Page N ---`-marked markdown from OCR. TOC
extraction is a text-pattern task (heading levels + page ranges over clean
markdown), so a text-only LLM is strictly better: higher throughput, lower RAM,
no vision tower, mature grammars. A VLM would only matter if we fed raw page
images instead of OCR text (e.g., a fallback to re-OCR a garbled TOC page), and
the only cleanly-licensed small VLM there is Qwen2.5-VL-7B (6 GB+, slow).

### 2.4 Verdict — models realistic on CPU + Intel Arc 140V

1. **Qwen3-4B (non-thinking)** — best overall: Apache-2.0, native JSON/tool,
   excellent CJK, 128K ctx, ~2.6 GB Q4 fits the iGPU, ~7–12 tok/s CPU.
2. **Qwen3-1.7B** — best CPU-speed fallback: ~1.3 GB, ~25–50 tok/s, adequate
   for a simple TOC schema.
3. **Phi-4-mini** — best structured-output model, but weak CJK (choose only for
   Latin/Romanized documents).
4. **Avoid:** Qwen2.5-3B + Qwen2.5-VL-3B (non-commercial), Llama 3.2 (no CJK),
   SmolLM2/3 (no CJK), Gemma 3 1B (EN-only).

---

## 3. Prompt + schema design — ép JSON có cấu trúc, chống số trang ảo

### 3.1 Structured-output / JSON-schema enforcement for small local models

Constrained decoding masks the logits of tokens that would violate a constraint
at each step — the model *cannot* emit invalid JSON. Verified methods:

- **llama.cpp GBNF** (native, C++, CPU): `--grammar` / `--grammar-file` /
  `-j --json-schema`; `llama-server` accepts `grammar`, `json_schema`,
  `response_format`. GBNF is a BNF extension with regex-like character classes
  and alternation. **Crucially for page grounding, JSON-schema integer
  `minimum`/`maximum` bounds expand into digit-by-digit alternatives** (e.g. for
  0–150: `"1" ([0-4] [0-9] | [5] "0")`), so page numbers can be constrained to
  any observed range. Caveats: unsupported keywords are silently skipped;
  `additionalProperties` defaults to false; and **the schema is not injected
  into the prompt** — the model still needs the structure described in the
  prompt text. ([llama.cpp grammars README](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md))
- **Outlines** (dottxt-ai, Python): `outlines.generate.json(model, schema)`
  builds an FSM from a JSON Schema/Pydantic/TypedDict and guarantees output
  validates. Local backends: Transformers (CPU) and LlamaCpp
  (`outlines.models.llamacpp(gguf, n_gpu_layers=0, n_threads=8)` — "optimized
  for CPU and resource-constrained environments"). Guarantees syntax, not
  semantics. ([Outlines README](https://raw.githubusercontent.com/dottxt-ai/outlines/main/README.md),
  [JSON-schema generation](https://deepwiki.com/dottxt-ai/outlines/3.2-json-schema-generation))
- **guidance** (Microsoft): `json(schema)` / `regex(...)` / `select(...)` force
  structure token-level; CPU via Transformers or llama.cpp (LLGuidance engine).
  Aims at small models (e.g. Phi-3) — "structured constraints let weak models
  focus on content, not syntax". ([guidance JSON docs](https://deepwiki.com/guidance-ai/guidance/5-json-and-structured-output),
  [Phi-3 CookBook Guidance intro](https://github.com/microsoft/Phi-3CookBook/blob/main/md/01.Introduce/Guidance.md))
- **SGLang / vLLM** — GPU serving engines; **not CPU-oriented**; avoid here.
- **HuggingFace Transformers `generate`**: no built-in JSON constraint; use
  `transformers-cfg` (epfl-dlab) `GrammarConstrainedLogitsProcessor`, CPU works.
  ([transformers-CFG](https://github.com/epfl-dlab/transformers-CFG))

### 3.2 Page-number grounding (chống hallucination số trang)

The strongest verified pattern is a **layered ground** — derive the allowed page
set from the document, put it in the prompt, constrain the decoder, cross-check:

1. **Constrain page numbers to the observed set via grammar.** GBNF integer
   range expansion (§3.1) makes a hallucinated page outside the observed set
   *impossible*; for a small gapped set, enumerate exact values with `|`
   alternation.
2. **"Known pages" whitelist in the prompt.** Feed `KNOWN PAGES: 1..186`
   (derived from the `--- Page N ---` markers) and instruct "never invent a page
   number". This is the grounding technique used by
   [@heripo/document-processor](https://www.npmjs.com/package/@heripo/document-processor),
   which accepts a known-pages list and a `sourceRefValidationMode` to verify
   generated references exist in the source.
3. **The numbers are literally in the OCR text.** Because TOC entries show
   `Chapter 1 … 5`, the model's job is *parsing, not arithmetic* — keep the
   markers in the prompt.
4. **Cross-check against the observed page list post-hoc:** every
   `page_start`/`page_end` must be a member of the `--- Page N ---` set; any
   value outside is a hard failure (resample / fallback).
5. **OCR hygiene upstream:** hallucination often originates in OCR noise, not
   the LLM — strip repeated boilerplate (headers/footers/copyright) and watch
   for bad-OCR signatures (ligature anomalies, spurious line-end hyphens)
   before extraction. ([OCR/parsing checklist](https://github.com/onestardao/WFGY/blob/main/ProblemMap/ocr-parsing-checklist.md))

### 3.3 Chunking long books — TOC-page isolation first

The dominant documented strategy is **index-first / TOC-driven**, never feeding
the whole book:

- Detect and isolate the TOC region first (keyword search + structure analysis
  for a list/table with page-number patterns, including multi-page TOCs) and
  **feed only those pages to the LLM** — a book TOC is typically <2k tokens,
  within a 1–4B model's context. Preserve indentation/hierarchy when converting
  the TOC to text so the model can infer part/chapter nesting. Examples:
  [PageIndex](https://github.com/NP-compete/pageindex) (scans first N pages,
  `--toc-check-pages: 20`), [RAGFlow TOC extraction](https://github.com/infiniflow/ragflow/blob/main/docs/guides/dataset/advanced/extract_table_of_contents.md),
  [md2idx](https://www.npmjs.com/package/md2idx).
- **Compute `page_end` in code, not in the LLM.** The TOC lists a start page
  per chapter; `page_end = next.page_start - 1` (last page for the final
  chapter). Having the model return only start pages removes the largest
  hallucination surface. This is exactly what `extract_curriculum()` already
  does with `entries[i+1]["page"] - 1`.

### 3.4 Self-consistency / verification

- **Self-consistency** (Wang et al. 2022, ICLR 2023): sample N paths at
  temperature >0, majority-vote the answer; correct answers converge while wrong
  ones scatter. For our case: N=5 at T≈0.5–0.7, key entries by `chapter_num`,
  take the modal `page_start`/`page_end` per chapter — **and only accept a page
  number if it is both the plurality AND in the observed whitelist**. Caveat:
  voting removes variance, not systematic bias — all samples can agree on the
  wrong value, hence the rule-based cross-check.
  ([arXiv:2203.11171](https://arxiv.org/abs/2203.11171))
- **Rule-based cross-check (hybrid verification):** run the existing regex scan
  of the TOC for `title…digits` pairs and diff against the LLM's JSON; resolve
  page-number disagreements in favor of the rule-based value when it's
  confident; flag LLM-only entries for review.
- **Sanity constraints (deterministic):** `page_start <= page_end`; page numbers
  monotonic across entries; `chapter_num` sequential (a skip indicates a dropped
  entry); every page value ∈ observed set.

### 3.5 Known failure modes of small LLMs on JSON + mitigations

Measured on Llama 3.1 8B over 1,000 extraction tasks: valid JSON only 64.2%
(missing closing brace 12.1%, trailing comma 8.7%, unquoted values 5.3%, extra
text 4.9%, wrong field names 3.1%, truncation 1.7%). Small models are much
worse: **llama3.2:3b produces incomplete JSON ~50% of the time; 1B "basically
cannot complete structured output tasks."**
([fine-tuning-json-output](https://www.ertas.ai/blog/fine-tuning-json-output),
[Escapement study](https://github.com/fulcrologic/escapement/blob/main/docs/structured-output-from-small-models.md))

The **"constraint tax"** paper (Qwen2.5-0.5B/1.5B, SmolLM2-1.7B) is the key
nuance: hard answer-only schema decoding **raised schema validity 61.5%→100%
but lowered answer accuracy 19.7%→11.0%**, and wrong-but-schema-valid outputs
rose 49.5%→88.9%; a calendar tool-call analogue dropped from 91.5% executable
accuracy (prompt-only JSON) to 48.0% (hard schema). Recommendation:
**"reason free, constrain late"** — solve first, constrain the packaging
afterward. ([arXiv:2605.26128](https://arxiv.org/abs/2605.26128))

**Mitigations in order:** (1) constrained decoding on the *page numbers* only
(grounded facts), not the whole schema; (2) validation → repair → retry
(`json-repair` succeeds 85–95% vs 40–60% naive retry); (3) split the task —
a first call (or rule scan) reasons, a second dedicated call only emits
schema-valid JSON from a compact summary ("small models drift less with less
context"); (4) give an escape hatch (`null` / `not_found`) so the schema doesn't
force invention.

### 3.6 Recommended pattern for a small CPU model

Pipeline: **rule-based TOC isolation → prompt with known-pages whitelist →
grammar-constrained decoding → deterministic verification → (optional)
self-consistency.** Exact prompt + GBNF snippet for `{part, chapter_num,
chapter_title, page_start, page_end}` with pages 1–186:

```
SYSTEM:
You are a table-of-contents parser for an OCR'd book. Your ONLY output is a
JSON array, each element {"part": int|null, "chapter_num": int,
"chapter_title": string, "page_start": int, "page_end": int}.
Output ONLY the JSON array. No prose. No markdown fences.

Page numbers in this book come from markers "--- Page N ---".
KNOWN PAGES: 1..186
Rules:
- page_start and page_end MUST be integers from KNOWN PAGES. Never invent one.
- page_start <= page_end. Entries appear in ascending page order.
- chapter_num are sequential (1, 2, 3, ...).
- The TOC lists a START page per chapter. Set page_end = next chapter's
  page_start - 1 (final chapter: the last page of the book).
- If a page number is unreadable, set it to null and continue.
- "part" is null when the book has no parts.
```

GBNF (llama.cpp `--grammar-file`) — page numbers hard-constrained to 1..186:

```
char      ::= [^"\\\x7F\x00-\x1F] | "\\" (["\\bfnrt] | "u" [0-9a-fA-F]{4})
string    ::= "\"" char* "\""
page-num  ::= [1-9] | [1-9] [0-9] | "1" [0-7] [0-9] | "18" [0-6]
chapter-num ::= [1-9] | [1-9] [0-9]
entry     ::= "{"
              " "? "\"part\"" ":" " " ( "null" | [1-9] [0-9]? ) ","
              " "? "\"chapter_num\"" ":" " " chapter-num ","
              " "? "\"chapter_title\"" ":" " " string ","
              " "? "\"page_start\"" ":" " " page-num ","
              " "? "\"page_end\"" ":" " " ( page-num | "null" )
              " "? "}"
root      ::= "[" " "? entry ("," " "? entry)* "]" " "?
```

Verification after decoding: strict `json.loads` → Pydantic validation →
whitelist membership → `page_start <= page_end` → monotonic order → sequential
`chapter_num` → rule-based regex cross-check → merge ranges in code.

---

## 4. Hybrid architecture recommendation — khuyến nghị kiến trúc

### 4.1 Escalation design

A layered, conservative-by-design pipeline that keeps the current rule-based
path as the default and escalates only on low confidence:

```
1. Rule scan (existing two-pass, generalized per §1):
   TOC dotted-anchor scan (课/章/unit/chapter + per-language lexicon)
   → body-heading fallback (## N章 etc.)
   → if entries found AND page-anchor confidence high → RETURN (no LLM).

2. Confidence gate: low/empty result OR page anchors unresolvable
   (dotted leaders mangled, unknown structure) → escalate.

3. SLM path (CPU, llama-cpp-python, Qwen3-4B Q4 non-thinking):
   a. Rule-detect the TOC region (Contents heading → Index) and extract
      KNOWN_PAGES from the --- Page N --- markers.
   b. Prompt the model with ONLY the TOC text + whitelist (§3.6), decode
      with a GBNF grammar that hard-constrains page numbers to KNOWN_PAGES.
   c. Deterministic verification: parse → validate → whitelist → monotonic
      → cross-check against the rule scan.
   d. On disagreement, the rule scan wins for page numbers when confident;
      LLM-only entries are flagged for review. Page_end always computed in code.

4. Empty at every level → empty curriculum map, lessons fall back to
   current behaviour (matches today's conservative contract).
```

### 4.2 Runtime comparison (verified against official docs)

| Runtime | CPU-only | Intel Arc/iGPU | Python API | Constrained decoding | License | Fit |
|---|---|---|---|---|---|---|
| **llama.cpp / llama-cpp-python / llama-server** | ✅ | ✅ SYCL (oneAPI) + **Vulkan (no oneAPI)**; LNL Arc verified | In-process + OpenAI HTTP | ✅ GBNF + JSON-schema grammar | MIT | **Best** |
| Ollama | ✅ | ⚠️ unofficial; SYCL PR pending; IPEX path dead | REST + Python client | ✅ JSON-schema `format` | MIT | Good CPU-only |
| ONNX Runtime GenAI | ✅ (INT4) | ⚠️ via DirectML EP (Windows) | In-process + server | ✅ LLGuidance (`json_schema`/`regex`) | MIT | Solid, more workflow |
| HF Transformers + accelerate | ✅ | ⚠️ XPU slow; fast path archived | In-process | ❌ needs Outlines/Guidance | Apache-2.0 | Workable but slow |
| OpenVINO / optimum-intel | ✅ | ✅ `"GPU"` device (iGPU/Arc) | In-process | ⚠️ JSON-schema claimed in GenAI (**unverified**) | Apache-2.0 | Good 2nd choice |
| **IPEX-LLM** | ✅ | (was) — **archived Jan 2026** | In-process | ❓ | Apache-2.0 | **Avoid** |
| vLLM / SGLang | vLLM CPU exp. | ❌ (Arc Pro only, Linux/Docker) | Server | ✅ | Apache-2.0 | No |

Sources: [llama.cpp SYCL backend](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md),
[llama-cpp-python](https://github.com/abetlen/llama-cpp-python),
[llama-server README](https://github.com/ggml-org/llama.cpp/blob/master/examples/server/README.md),
[Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[Ollama SYCL issue #16930](https://github.com/ollama/ollama/issues/16930),
[ORT GenAI quickstart](https://mintlify.wiki/microsoft/onnxruntime-genai/quickstart),
[ORT GenAI constrained decoding](https://mintlify.wiki/microsoft/onnxruntime-genai/guides/constrained-decoding),
[optimum-intel v2 blog](https://huggingface.co/blog/jeffboudier/optimum-intel-v2),
[OpenVINO GenAI intro](https://openvinotoolkit.github.io/openvino.genai/docs/getting-started/introduction/),
[intel/ipex-llm (archived)](https://github.com/intel/ipex-llm),
[Intel LLM-Scaler](https://github.com/intel/llm-scaler).

### 4.3 Is the Arc 140V iGPU worth it for a ≤4B model? — No

The Arc 140V is bandwidth-bound (~137 GB/s unified LPDDR5X), so small-model
throughput is low. Measured figures:

| Model | Hardware | Backend/quant | tok/s | Source |
|---|---|---|---|---|
| Llama 3.2 1B | Lunar Lake iGPU (Arc 140V-class) | llama.cpp Vulkan Q4 | 42–48.5 | [lhl/intel-inference](https://github.com/lhl/intel-inference) |
| Qwen2.5 3B | Arc 140V iGPU | Vulkan FP32 | ~7 | [canitrun.dev/arc-140v](https://canitrun.dev/gpus/arc-140v/) |
| Llama 3.2 3B | Arc 140V iGPU | Vulkan FP32 | ~6.5 | [canitrun.dev/arc-140v](https://canitrun.dev/gpus/arc-140v/) |
| Phi-4-mini (3.8B) | Arc 140V iGPU | Vulkan FP32 | ~5.5 | [canitrun.dev/arc-140v](https://canitrun.dev/gpus/arc-140v/) |
| Qwen2.5 3B | desktop CPU | llama.cpp Q4_K_M | ~12 | [computingforgeeks](https://computingforgeeks.com/run-local-llm-llama-cpp/) |

The only measured Arc 140V numbers are unquantized (FP32) via Vulkan (~5–7
tok/s for 3–4B) — **no faster than a modern CPU at Q4 (~10–15 tok/s)**. A direct
Q4-GGUF-on-Arc-140V 3B measurement was **not found** (inferred ~1.5–2× over CPU
from the 1B Q4 result). For a curriculum-map extraction (~a few hundred output
tokens), CPU at ~12 tok/s completes in ~30 s — trivially fast for an offline
batch job. The iGPU buys nothing we need and costs oneAPI/Vulkan build
complexity. **Recommendation: CPU-only now; Vulkan backend (no oneAPI) only if
we later run 7B+ models or interactive chat.**

### 4.4 Is an SLM worth it at all vs broadening the rules? — As a fallback, yes

Evidence and reasoning:

- A published case study on a course-book TOC shows exactly where naive rules
  break: a rule-based parser **demoted the "Table of Contents" heading and
  hallucinated a markdown table around every TOC entry** (score 0.787 vs 0.998
  for a stronger pipeline) — TOCs are a genuinely weak spot for heuristics, but
  the failure is recoverable with better heading/pagination rules.
  ([nutrient.io case study](https://www.nutrient.io/blog/pdf-extraction-document-case-studies/))
- An arXiv evaluation of PDF→RAG pipelines found **hierarchy-aware structure
  (headings) is the dominant factor in downstream accuracy**: Docling +
  hierarchical splitting hit 94.1% vs 86.2% for a naive loader — i.e., the
  heading-hierarchy piece this repo already built is the highest-value piece.
  ([arXiv:2604.04948](https://arxiv.org/abs/2604.04948))
- Pragmatics: the repo's book TOCs are OCR'd, one page, consistent formatting;
  a broadened regex lexicon + heading-hierarchy heuristic handles the common
  case at zero runtime cost and is unit-testable (matches the pytest / ≥80%
  coverage workflow). A 1.7–4B Q4 GGUF as a **fallback** for messy TOCs is cheap
  with `llama-cpp-python` and does **not need the iGPU**.

**Verdict:** broaden the rules first (free, fast, testable); keep a CPU-only
small-LLM fallback for TOCs the heuristic can't parse. For a 10–20 chapter map,
the SLM is not worth it as the default path — only as an escalation layer.

---

## Khuyến nghị cuối (Final recommendation)

1. **Phase 1 — generalize the rule-based path (no LLM, no new deps):**
   per-language structural-marker lexicon (JP/KO/ZH/EN) in `curriculum_service.py`;
   content-association cross-check (a TOC candidate heading must reappear in the
   body); Flat/Ordered/Divided style handling for TOCs without dot leaders.
   Unit-test each language with a fixture. **This covers the 10–20 chapter map
   for the common case.**
2. **Phase 2 — SLM escalation fallback:** `llama-cpp-python` (MIT), **CPU-only**,
   **Qwen3-4B Q4_K_M non-thinking** (Apache-2.0; or Qwen3-1.7B for speed).
   Escalate only when the rule scan returns empty/low-confidence. Feed only the
   TOC pages + `KNOWN_PAGES` whitelist; decode with a GBNF grammar hard-
   constraining page numbers to the observed set; verify deterministically;
   rule-scan wins on page-number disagreements; compute `page_end` in code.
3. **Do not:** use Qwen2.5-3B / Qwen2.5-VL-3B (non-commercial), adopt IPEX-LLM
   (archived), invest in the Arc iGPU for a ≤4B model, or adopt any PDF→markdown
   library (input mismatch + license blockers).
4. **Defer:** a VLM is unnecessary while OCR text is available; revisit only for
   a garbled-TOC re-OCR fallback (GOT-OCR2, 0.58B Apache-2.0).

## Sources & open questions

- All claims above carry their source URL inline. The three most load-bearing
  claims were verified directly during this research: **IPEX-LLM archived Jan 28
  2026** ([intel/ipex-llm](https://github.com/intel/ipex-llm)), **Qwen2.5-3B
  non-commercial license** ([LICENSE](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/raw/main/LICENSE)),
  and **Qwen3-4B Apache-2.0 + toggleable thinking**
  ([model card](https://huggingface.co/Qwen/Qwen3-4B)).
- **Not verified** (gaps worth closing before build):
  - Direct Q4-GGUF tok/s of a 3B model on the Arc 140V iGPU (inferred from 1B Q4 +
    bandwidth scaling; only unquantized FP32 Vulkan figures were found).
  - OpenVINO GenAI's JSON-schema-constrained-decoding claim (no primary doc found).
  - A head-to-head "LLM vs rules for TOC extraction" benchmark (the Docling-vs-X
    comparisons are parser-vs-parser; LLM evidence is downstream-QA-based).
  - Arc 140V memory footprint of Qwen3-4B with a 128K KV cache (Q4 fits VRAM;
    long-context KV growth not measured).
- **Next experiments (mirror the repo's H1/H2/H3 habit):**
  - H4: content-association cross-check measurably improves TOC recall when the
    OCR mangles dot leaders (proxy: compare against the two known books).
  - H5: Qwen3-4B grammar-constrained output matches rule-based page numbers on
    the GOI + N3 Kanji books; measure precision on a synthetic multi-language TOC
    fixture set (JP/KO/ZH/EN).
  - H6: CPU-only SLM extraction latency stays < 60 s on a 200-page book's TOC.
