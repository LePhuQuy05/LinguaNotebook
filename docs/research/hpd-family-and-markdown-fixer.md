# Research: Two-Stage PDF-to-Markdown — HPD/Paddle Family (Stage 1) + Small-LLM Markdown Fixer (Stage 2)

**Status**: research (ready for a validation experiment)
**Created**: 2026-08-01
**Parent**: 001-lingua-notebook (PDF parsing subsystem)
**Context**: Follow-up to `docs/research/pdf-to-markdown-options.md` (which established Qwen2.5-VL-7B via llama.cpp SYCL as the quality path at ~200 s/page and HPD as the speed path at ~53 s/page). This document evaluates the user's proposal: **Stage 1 = fast parsing model from the HPD/PaddlePaddle family; Stage 2 = a small text-only LLM that repairs the OCR text and formats it into proper markdown for RAG.** All hardware-support and model claims below were verified against primary sources (model cards, official docs, GitHub issues/PRs, papers); estimates are labeled as estimates.

---

## TL;DR / Recommendation

1. **HPD-Parsing has only one size: 1B** (InternVL3.5-1B backbone = 0.3B InternViT + Qwen3-0.6B-derived LLM). There is **no 0.5B variant** anywhere in the official repo or model card. Its native output is `<BLOCK>/<CHILD>`-structured tokens that the repo's own `eval/hpd_to_markdown.py` converts to per-page markdown — so the model *does* produce layout structure (blocks, coordinates, reading order); the user's current pipeline just isn't consuming it. Stage 2 can build on those structure hints for free.
2. **PaddleOCR-VL is 0.9B only** — "1.6" is the **version number**, not a 1.6B model. It outputs markdown natively, officially supports Japanese (109 languages), and scores 96.33% on OmniDocBench v1.6 (which is **English/Chinese-only**). But on this machine it is **CPU-only**: PaddlePaddle has no Intel GPU backend (verified — Paddle's "XPU" is Baidu Kunlun, not Intel), and its only public CPU speed anchor (~64 s/page on a Xeon via OpenVINO) suggests it will be **slower, not faster**, than HPD-1B on the user's XPU (53 s/page). Keep HPD-1B as Stage 1.
3. **Stage 2 is viable and worth building**, but with corrected throughput expectations: a 1.5–3B text model on the Arc 140V iGPU via llama.cpp SYCL reaches **~15–34 tok/s** (measured anchors on this exact GPU family: 1.5B = 34 tok/s, 2B = 25 tok/s, 8B = 11 tok/s), **not** the 40–60 tok/s assumed in the prompt. At ~600–1000 output tokens/page that is still only **~25–60 s/page** — acceptable.
4. **Recommended pipeline**: HPD-1B on XPU (existing, 53 s/page) → convert its `<BLOCK>/<CHILD>` output with `hpd_to_markdown.py` (or pass block hints alongside the text) → **Qwen2.5-3B or Qwen3-4B Q4_K_M via the already-working llama.cpp SYCL `llama-server`** → clean Japanese markdown for RAG. Expected total: **~4–5 h per 186-page book vs ~10.3 h** for full-book Qwen2.5-VL-7B (**~2.2–2.5x speedup**) at estimated 90–95% effective Japanese accuracy (from ~85% raw) — pending a 10–20 page A/B validation.
5. **Llama-3.2-3B is disqualified** for this job: its officially supported languages are English, German, French, Italian, Portuguese, Hindi, Spanish, Thai — **Japanese is not among them**. Phi-3.5-mini (23 languages incl. Japanese) and the Qwen small models are the candidates.

---

## Comparison table — Stage 1 models (HPD/Paddle family)

| Model | Params | Backend on this machine | Speed (per page) | Japanese quality (evidence) | Markdown output | Verdict |
|---|---|---|---|---|---|---|
| **HPD-Parsing-1B** (current) | 1B (0.3B vision + 0.8B LLM) | PyTorch **XPU** (transformers ref impl; already working) | **53 s/page (user-measured)** | ~85% (user-measured); **no JP evidence in training data** — model card tagged `en`,`zh` only; OmniDocBench v1.6 (its eval set) is EN/ZH-only | Not native — `<BLOCK>/<CHILD>` tokens → markdown via included `eval/hpd_to_markdown.py` | **Keep as Stage 1** (fastest available on this hardware) |
| **PaddleOCR-VL-1.6-0.9B** | 0.9B (SigLIP-class NaViT encoder + ERNIE-4.5-0.3B) | **CPU only** (PaddleOCR `doc-parser`; no Intel GPU backend; vLLM path is NVIDIA-docker-only; transformers path is element-level only, no page parsing) | ~60–120 s/page (est.; only anchor: ~64 s/page on Xeon Gold 6242 via an OpenVINO port) | Officially supports **109 languages incl. Japanese**; OmniDocBench v1.6 **96.33%** (EN/ZH); ParseBench mean 67.4 but **text formatting only 54.6** | **Native** (`res.save_to_markdown()` / JSON) | Not faster than HPD here; better JP story + native markdown; useful fallback / comparator |
| PP-OCRv6 (OCR engine only) | ~90M-class | CPU/Paddle | seconds/page | JP included in 109 langs | None (no layout/structure) | Not a stage-1 replacement (no parsing); used inside MinerU |
| *Qwen2.5-VL-7B (reference, from prior research)* | 7B | llama.cpp **SYCL** | ~200 s/page (user-measured) | ~100% (user-measured) | Prompt-driven | The quality ceiling; Stage 2 does not aim to beat it, only to approach it at 1/2 the time |

---

## 1. HPD-Parsing model family — findings

**Primary sources**: [HPD-Parsing model card](https://huggingface.co/PaddlePaddle/HPD-Parsing), [HPD-Parsing paper (arXiv 2607.18839)](https://arxiv.org/abs/2607.18839), code in [PaddlePaddle/PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR).

- **What it is**: PaddleOCR's unified VLM document parser (released July 2026), built for high-throughput scanned-document parsing. Architecture: InternVL3.5-1B backbone (0.3B InternViT visual encoder + 0.8B LLM adapted from Qwen3-0.6B, 28 layers, GQA), dynamic tile cropping up to 24×448² tiles, i.e. up to ~4,800 visual tokens per page.
- **Variants: one size only — 1B.** The model card lists no 0.5B or 2B checkpoint. The only secondary artifact is `P-MTP` (the speculative-decoding draft head, weights also embedded in the main checkpoint). The "family" = HPD-Parsing-1B + the sibling PaddleOCR-VL series + the PP-OCRv6 engine.
- **Speed**: the headline numbers are **batch throughput on NVIDIA A800 via vLLM** (peak 4,752 TPS / 2.68 pages/s at batch 512; 3.06x its own autoregressive baseline; 1.62x DeepSeek-OCR-2). **None of this transfers to single-page latency on an iGPU** — the user's measured 53 s/page on XPU is the only relevant number. The decoding-paradigm win (fewer steps via `<FORK>` branches + P-MTP) is real but already baked into the user's 53 s/page if P-MTP is enabled.
- **Markdown**: **no HPD variant outputs markdown directly.** Predictions are `<BLOCK>...<CHILD>...` tokens carrying region categories, normalized coordinates, and reading order; the repo ships [`eval/hpd_to_markdown.py`](https://huggingface.co/PaddlePaddle/HPD-Parsing/blob/main/eval/hpd_to_markdown.py) to convert to per-page markdown (used for OmniDocBench end-to-end eval). **Implication: the user's pipeline is likely throwing away layout structure the model already emits** — a free Stage-1.5 improvement before any LLM fixer.
- **Japanese**: the model card is tagged `en`/`zh` only; the paper and OmniDocBench v1.6 are **English/Chinese benchmarks**; no Japanese-specific training or eval is mentioned anywhere. This is consistent with the user's ~85% Japanese accuracy ceiling — HPD-1B's quality on Japanese is an *unverified extrapolation* of an EN/ZH model. Accuracy note: even on its home benchmark, HPD-1B (94.91% OmniDocBench v1.6) trails the *pipeline* leader PaddleOCR-VL-1.6 (96.33%), and its **TableTEDS is its weakest metric (91.35 vs PaddleOCR-VL's 94.8)** — tables are exactly what Stage 2 can repair with text-level reasoning.

## 2. PaddleOCR-VL — findings

**Primary sources**: [PaddleOCR-VL model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL), [PaddleOCR-VL-1.6 model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6), [PaddleOCR-VL paper (arXiv 2510.14528)](https://arxiv.org/abs/2510.14528), [official docs](https://github.com/PaddlePaddle/PaddleOCR/blob/c1664488/docs/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.en.md), [PaddlePaddle hardware support table](https://paddlepaddle-org-cn.bj.bcebos.com/documentation/docs/zh/guides/hardware_support/hardware_info_cn.html).

- **Size: 0.9B, period.** "1.6" is the release version. Confirmed across the official card ("0.9B Ultra-Compact VLM", 1.0B rounded in metadata), the docs ("maintains an ultra-compact 0.9B-parameter VLM", "drop-in replacement"), and the architecture breakdown: NaViT-style dynamic-resolution visual encoder (SigLIP-so400m-class, 27 layers) + ERNIE-4.5-0.3B decoder (18 layers) ≈ 0.9B total. The one "1.6B" mention online is a third-party error conflating version and size.
- **Native markdown: yes.** `res.save_to_markdown(...)` / `res.save_to_json(...)` / CLI `paddleocr doc_parser -i <url> --pipeline_version v1.6`. Tasks: `ocr | table | chart | formula`. Page-level parsing requires the official PaddleOCR `doc-parser` pipeline (`paddleocr[doc-parser]>=3.4.0`, `PaddleOCRVL(pipeline_version="v1")`); the transformers path **only supports element-level recognition**, not full pages.
- **Japanese: officially supported** — "supports 109 languages, including but not limited to Chinese, English, Japanese, Latin, and Korean." Caveat: the *page-level* benchmark scores (96.33% OmniDocBench v1.6, olmOCR-bench Old Scans 38.6, ParseBench mean 67.43 / text formatting 54.64) are not Japanese-specific evidence; the 109-language claim is a vendor claim.
- **Speed on CPU — no Intel GPU backend (verified)**: the PaddlePaddle hardware table lists NVIDIA as the only GPU vendor; "XPU" in Paddle terms = **Baidu Kunlun** chips (K200/R200), not Intel XPU. The PaddleOCR-VL card never mentions Intel. Page parsing on this machine is therefore **PaddlePaddle CPU (or a community OpenVINO port)**. Public anchor: ~64 s/page for PaddleOCR-VL-1.5 via the [OpenVINO port on a Xeon Gold 6242](https://huggingface.co/Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO) — and Paddle-native CPU is typically *slower* than an OpenVINO-optimized port. Expect **60–120+ s/page on the user's Lunar Lake CPU** (estimate; no public number exists for this chip).
- **Verdict**: PaddleOCR-VL-1.6 is the *quality* upgrade of the HPD lineage (better JP story, native markdown, SOTA EN/ZH benchmarks) but on this hardware it is **not meaningfully faster than HPD-1B** — it's a CPU-bound fallback, not a speed path. It remains the best answer if HPD-1B's ~85% JP accuracy proves uncorrectable by Stage 2.

## 3. Stage 2 — "markdown fixer" small-LLM options

### Throughput anchors on the Arc 140V iGPU (llama.cpp SYCL)

| Anchor (primary source) | Model | tok/s |
|---|---|---|
| [llama.cpp PR #13383 benchmark, Lunar Lake 140V, `-mmp 0 -ngl 99 -t 8`](https://github.com/ggml-org/llama.cpp/pull/13383) | qwen2-1.5B Q4_0 | **34.05** |
| same | gemma2-2B Q4_K | **25.00** |
| same | llama-8B Q4_K-Medium | **11.10** |
| [llama.cpp PR #20571 (fused GDN kernel), 140V](https://github.com/ggml-org/llama.cpp/pull/20571) | Qwen3.5-0.8B Q4_K_M, decode | 54.0 (SSM model — not applicable to dense text models) |
| [intel-llm project (precompiled SYCL fp16 binaries)](https://github.com/julian-corbet/intel-llm) | 1.5B | ~25 |
| [Ollama benchmark, dual discrete Arc A770](https://github.com/okazaki0yumemi1/ollama-benchmark-intel-a770) | Qwen3-4B | 23.0 (discrete card — upper bound context only; iGPU is roughly half this) |
| User's own (from prior research) | Qwen3.5-A3B MoE (SSM-bottlenecked) | ~27 |

**Takeaway**: dense 1.5–1.7B models: **~25–34 tok/s**; dense 3–4B models: **~15–22 tok/s**. Prefill on dense models is fast (hundreds of tok/s; the slow 23 tok/s prefill in PR #20571 was specific to the SSM model's CPU-fallback ops). **The user's 40–60 tok/s assumption is optimistic; ~2x lower is the honest estimate.** Also note: dense text models avoid the SSM-layer bottleneck that capped the user's Qwen3.5-A3B at 27 tok/s — text-only Qwen2.5/Qwen3 models get the fully-fused SYCL GEMM path.

### Candidate models (verified against model cards)

| Model | Params | Japanese support (primary source) | Q4_K_M size (approx.) | Est. tok/s (Arc 140V SYCL) | Notes |
|---|---|---|---|---|---|
| **Qwen2.5-1.5B** | 1.54B | **Explicit** — "Multilingual support for over 29 languages" incl. Japanese ([card](https://huggingface.co/Qwen/Qwen2.5-3B) lists it) | ~1.0 GB | **25–34** | Speed pick; weakest reasoning of the group |
| **Qwen2.5-3B** | 3.09B | **Explicit** (same 29-language list incl. Japanese) | ~1.9 GB | **18–25** | **Recommended default**: Japanese-native, enough capacity for context-based kanji disambiguation |
| **Qwen3-1.7B** | 1.7B | **Explicit** — "119 languages and dialects", Japanese listed under "Other" ([Qwen3 blog](https://qwenlm.github.io/blog/qwen3/)) | ~1.2 GB | **25–34** | Newer training (hybrid thinking mode; disable for speed) |
| **Qwen3-4B** | 4.0B | **Explicit** (same 119-language family) | ~2.6 GB | **15–22** | Strongest fixer candidate; 32K native context; Q4 fits trivially in 16 GB |
| **Phi-3.5-mini** | 3.8B | **Explicit** — 23 languages incl. Japanese ([card](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)); multilingual MMLU 55.4 | ~2.2 GB | **13–18** | Viable; Japanese quality second-tier vs Qwen |
| **Llama-3.2-3B** | 3.2B | **NOT officially supported** — card lists only EN/DE/FR/IT/PT/HI/ES/TH ([card](https://huggingface.co/meta-llama/Llama-3.2-3B)); Japanese unconfirmed in pretraining | ~2.0 GB | ~18–22 | **Disqualified** for a Japanese fixer |

### Would a 1.5–3B text model be smart enough?

Evidence from the Japanese post-OCR-correction literature (all primary sources):

- **JaPOC benchmark** (Fujitake, PRICAI 2024, [arXiv 2409.19948](https://ar5iv.labs.arxiv.org/html/2409.19948)): on noisy real-world Japanese OCR (26.6–72% raw accuracy), a fine-tuned Japanese T5 raised accuracy **85.4% → 94.8%**. Critical caveat: **over-correction actively degrades output when OCR is already good** — correction must be conservative.
- **"Beyond OCR"** (2024, classical Japanese documents, [CiNii](https://cir.nii.ac.jp/crid/1050865508277688832?lang=en)): LLM-based OCR refiners (7–14B, fine-tuned) significantly reduced CER, especially katakana/kanji misreads — the same error classes the user sees with HPD.
- **llm_aided_ocr** ([repo](https://github.com/Dicklesworthstone/llm_aided_ocr)) — the canonical open-source OCR+LLM pipeline: chunk → LLM correction ("fix OCR-induced errors; maintain structure") → markdown formatting → LLM quality assessment; supports local llama.cpp with grammars. Its author's measurements show LLM correction gains are **language-dependent** (English 7–58% CER reduction; Finnish ~0) and warns LLMs "fix" correct text — hence edit-ratio tracking.
- **JSAI 2025** ([paper](https://www.jstage.jst.go.jp/article/pjsai/JSAI2025/0/JSAI2025_4A3GS1004/_pdf/-char/en)): Japanese document pipeline with OCR → VLM → markdown, noting Japanese-specific layout pitfalls (UI images misclassified as tables) — relevant to textbook pages with illustrations.
- **Why small models can work here**: HPD's errors on Japanese are mostly *kanji confusions with strong n-gram context* (e.g. visually similar kanji) and *missing structure* — exactly the errors a text model corrects by context, unlike pure recognition errors. Table reconstruction is a *formatting* task, and HPD's `<BLOCK>/<CHILD>` tokens already delimit table regions — the fixer formats, not re-recognizes. Text-only means the fixer **cannot** re-check the image: errors with no contextual signal survive. That residual is Qwen2.5-VL's niche.
- **Honest expectation**: raw HPD JP accuracy ~85% → **~90–95% effective after the fixer** (estimate; the JaPOC-style gain was +9.4 points on worse raw OCR; nothing is published for exactly this model pair). Must be measured on 10–20 pages before committing.

## 4. End-to-end feasibility — 186-page textbook

| Phase | Model | Per page | 186 pages | Basis |
|---|---|---|---|---|
| Stage 1 | HPD-Parsing-1B on XPU | 53 s | **~2.7 h** | user-measured |
| Stage 2 | Qwen2.5-3B / Qwen3-4B, Q4_K_M, SYCL | prefill ~2–5 s + ~600–1000 output tokens at 15–25 tok/s ≈ **25–60 s** | **~1.3–3.1 h** | anchored interpolation (PR #13383) |
| **Total** | | ~80–115 s | **~4–6 h** | |
| *Reference: Qwen2.5-VL-7B full-book* | | ~200 s | *~10.3 h* | user-measured |

- **Soundness of the estimate**: the pipeline structure is sound and the stage-1 anchor is measured; the two corrections to the user's proposal are (a) token throughput is ~15–34 tok/s, not 40–60, and (b) stage-2 output is ~600–1000 tokens/page (Japanese markdown of a textbook page), not ~500 — net effect: stage 2 is ~2–4x the user's 10–15 s/page estimate. Total ~4–6 h vs 10.3 h still holds as a **~2x speedup**, rising toward 2.5x if output is kept terse.
- **GPU contention**: both stages want the same iGPU; run sequentially (simple) or overlap stage 2 on later pages while stage 1 finishes earlier ones (they're the same device — marginal gain; the CPU could carry a 1.5B fixer at ~10–15 tok/s if parallelism is ever needed).
- **Papers/blogs on the OCR → LLM pattern**: [llm_aided_ocr](https://github.com/Dicklesworthstone/llm_aided_ocr), [deepresearch-flow (post-OCR fix stage: fix → fix-math → fix-mermaid → fix)](https://github.com/nerdneilsfield/ai-deepresearch-flow), [JSAI 2025 Japanese manual OCR+VLM pipeline](https://www.jstage.jst.go.jp/article/pjsai/JSAI2025/0/JSAI2025_4A3GS1004/_pdf/-char/en), [JaPOC](https://ar5iv.labs.arxiv.org/html/2409.19948), [ocr-bench (PaddleOCR-VL evals incl. old scans)](https://github.com/davanstrien/ocr-bench/blob/99f7550c/experiments/olmocr-bench-oldscans/BENCHMARKING.md). No paper was found for exactly "HPD + Japanese + LLM fixer"; the pattern is well-established, the specific model pairing is not published.

## 5. Pipeline design (two-stage)

```
scanned page (150-200 DPI render)
   │  Stage 1 (XPU, existing code path)
   ▼
HPD-Parsing-1B  →  <BLOCK>/<CHILD> tokens (+ region coords/reading order)
   │
   ├─ 1.5-optional: eval/hpd_to_markdown.py → markdown skeleton (structure for free)
   └─ or: pass raw text + block hints (table regions, header/footer) to Stage 2
   │
   ▼  Stage 2 (llama.cpp SYCL, llama-server sidecar, OpenAI-compatible endpoint)
Qwen2.5-3B / Qwen3-4B Q4_K_M  (text-only, no mmproj)
   │  per-page call: 1 prompt, ~2-5 s prefill + 25-60 s generation
   ▼
clean Japanese markdown  →  RAG ingest
```

**Fixer prompt sketch (Japanese-specific)**:

```
SYSTEM: You are a post-OCR text repairer for Japanese language textbooks.
Rules:
- Output ONLY markdown, nothing else.
- Preserve the original Japanese text exactly. NEVER translate, explain, or
  modernize. Double-check that no sentence ends up in English.
- Fix only clear OCR errors (wrong kanji/kana, broken words) using context.
  Do not rewrite correct text.
- Keep furigana as-is (e.g. 漢字（かんじ）). Do not invent furigana.
- Reconstruct tables as markdown tables using the provided block hints.
  If a cell is uncertain, keep the best guess; do not fill gaps.
- Convert region hints to headings (page titles -> #, section titles -> ##).
- Drop running page headers/footers and page numbers.
- If the input is already clean, return it unchanged.

USER:
<HPD block hints: table regions, heading candidates, reading order>
<HPD OCR text for the page>
```

**Hallucination controls** (from llm_aided_ocr + JaPOC findings):
- Conservative-instruction prompt (above) plus a *no-translate* double-check line — LLMs otherwise drift Japanese into English.
- Diff each page's output vs input; **flag pages whose edit ratio exceeds ~10%** for human review (over-correction is the documented failure mode when OCR is already good).
- Optionally constrain with a llama.cpp grammar (markdown outline) for the structure pass.
- Chunk at page level (or split long pages at `<BLOCK>` boundaries); page-level context is what makes context-based kanji repair work.

## 6. Risks / unknowns

1. **Fixer quality gain on Japanese is the key unknown** — JaPOC-scale gains (+9 points) came from fine-tuned models on worse raw OCR; a zero-shot 3B model on HPD output at ~85% is unproven. A/B test 10–20 pages against Qwen2.5-VL-7B before the full run.
2. **`hpd_to_markdown.py` on Japanese pages** is untested — its structure hints (EN/ZH-oriented training) may be noisy; the fixer must tolerate that.
3. **PaddleOCR-VL CPU speed on Lunar Lake is unverified** (only the Xeon/OpenVINO anchor exists) — if Stage 1 were ever switched to it, measure first.
4. **SYCL prefill on small dense models** should be fast but is build-version-dependent — run `llama-bench` locally on the chosen GGUF before scaling.
5. **Fundamental limit**: a text-only fixer cannot see the image; residual recognition errors with no contextual signal survive. If the target is ~100% JP accuracy, Qwen2.5-VL-7B remains the only verified path (at ~2x the total time).
6. HPD-1B and PaddleOCR-VL license/usage are Apache-2.0 (PaddleOCR repo/cards) — no license blocker found.

## Sources (primary)

- [HPD-Parsing model card (HF) — 1B only, `<BLOCK>/<CHILD>` output, `eval/hpd_to_markdown.py`, A800 vLLM throughput](https://huggingface.co/PaddlePaddle/HPD-Parsing)
- [HPD-Parsing paper — Hierarchical Parallel Document Parsing (arXiv 2607.18839)](https://arxiv.org/abs/2607.18839)
- [PaddleOCR-VL model card — 0.9B, 109 languages incl. Japanese, `save_to_markdown`, CUDA/CPU deployment](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)
- [PaddleOCR-VL-1.6 model card — 96.33% OmniDocBench v1.6, ParseBench 67.43/54.64, transformers=element-level only](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)
- [PaddleOCR-VL paper (arXiv 2510.14528)](https://arxiv.org/abs/2510.14528)
- [PaddleOCR official docs — PaddleOCR-VL-1.6 (0.9B, drop-in replacement)](https://github.com/PaddlePaddle/PaddleOCR/blob/c1664488/docs/version3.x/algorithm/PaddleOCR-VL/PaddleOCR-VL-1.6.en.md)
- [PaddlePaddle hardware support table — NVIDIA only GPU vendor; XPU = Baidu Kunlun; no Intel GPU](https://paddlepaddle-org-cn.bj.bcebos.com/documentation/docs/zh/guides/hardware_support/hardware_info_cn.html)
- [PaddleOCR-VL-1.5 OpenVINO port — ~64 s/page Xeon Gold 6242 (CPU anchor)](https://huggingface.co/Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO)
- [llama.cpp PR #13383 — SYCL benchmarks on Lunar Lake 140V (1.5B=34, 2B=25, 8B=11 tok/s)](https://github.com/ggml-org/llama.cpp/pull/13383)
- [llama.cpp PR #20571 — GDN fused kernel on 140V (0.8B decode 54 tok/s)](https://github.com/ggml-org/llama.cpp/pull/20571)
- [intel-llm — precompiled SYCL llama.cpp, ~25 tok/s 1.5B on Lunar Lake](https://github.com/julian-corbet/intel-llm)
- [Ollama benchmark — Qwen3-4B 23 tok/s on dual Arc A770 (discrete-card context)](https://github.com/okazaki0yumemi1/ollama-benchmark-intel-a770)
- [Qwen2.5-3B model card — 29+ languages incl. Japanese](https://huggingface.co/Qwen/Qwen2.5-3B)
- [Qwen3 blog — 119 languages incl. Japanese; dense sizes 0.6B/1.7B/4B/8B/14B/32B](https://qwenlm.github.io/blog/qwen3/)
- [Qwen3-4B model card](https://huggingface.co/Qwen/Qwen3-4B)
- [Phi-3.5-mini model card — 23 languages incl. Japanese, multilingual MMLU 55.4](https://huggingface.co/microsoft/Phi-3.5-mini-instruct)
- [Llama-3.2-3B model card — 8 officially supported languages, Japanese absent](https://huggingface.co/meta-llama/Llama-3.2-3B)
- [JaPOC: Japanese Post-OCR Correction Benchmark (PRICAI 2024, arXiv 2409.19948) — T5 correction 85.4→94.8%, over-correction caveat](https://ar5iv.labs.arxiv.org/html/2409.19948)
- [Beyond OCR: LLM refiner for classical Japanese (2024)](https://cir.nii.ac.jp/crid/1050865508277688832?lang=en)
- [llm_aided_ocr — OCR → chunk → LLM correction → markdown → QA, local llama.cpp support](https://github.com/Dicklesworthstone/llm_aided_ocr)
- [deepresearch-flow — post-OCR fix stage ordering](https://github.com/nerdneilsfield/ai-deepresearch-flow)
- [JSAI 2025 — Japanese document OCR+VLM→markdown pipeline](https://www.jstage.jst.go.jp/article/pjsai/JSAI2025/0/JSAI2025_4A3GS1004/_pdf/-char/en)
- [ocr-bench — PaddleOCR-VL evals on old-scans benchmark](https://github.com/davanstrien/ocr-bench/blob/99f7550c/experiments/olmocr-bench-oldscans/BENCHMARKING.md)
- Prior work: [docs/research/pdf-to-markdown-options.md](file:///D:/LanguageNotebook/docs/research/pdf-to-markdown-options.md)

*Verification note: "Paddle has no Intel GPU backend", "PaddleOCR-VL = 0.9B (1.6 is a version)", "HPD-Parsing = 1B only", "Llama-3.2-3B lacks official Japanese", and the Lunar Lake tok/s anchors were each checked against the cited primary sources. Per-page speed figures other than the user's measured 53 s (HPD/XPU) and ~200 s (Qwen2.5-VL-7B) are labeled estimates.*
