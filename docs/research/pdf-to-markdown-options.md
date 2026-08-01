# Research: PDF-to-Markdown Options for Intel Arc + Japanese Textbooks

**Status**: research (ready for agent work)
**Created**: 2026-08-01
**Parent**: 001-lingua-notebook (PDF parsing subsystem)
**Context**: Follow-up to `specs/003-marker-migration/` (archived) and `specs/004-hybrid-parser/` — HPD quality ceiling (~80-85% Japanese accuracy) cannot be fixed in-model; this document evaluates replacement OCR/conversion paths that run on the user's actual hardware.

---

## TL;DR / Recommendation

| Rank | Option | Why |
|------|--------|-----|
| 1 | **llama.cpp SYCL server + Qwen2.5-VL-7B GGUF** (via `llama-server.exe`) | Best Japanese OCR quality available on this hardware (dense VLM, not an OCR head), officially supported on Lunar Lake iGPU by llama.cpp's SYCL backend, ~2x faster than Vulkan, no oneAPI install needed (prebuilt Windows zip). ~6 GB model fits the 16 GB shared memory. |
| 2 | **PaddleOCR-VL (0.9B / 1.6) via PaddlePaddle CPU** | Same vendor/stack as the current HPD pipeline, 109-language support including Japanese, native markdown output, OmniDocBench SOTA claims. CPU-only on Intel hardware (no Intel GPU backend exists in PaddlePaddle) — slower than the VLM route but a drop-in architectural upgrade over HPD. |
| 3 | **MinerU v3.4 (CPU pipeline backend)** | Pure-CPU PDF-to-markdown with real structure handling (tables, LaTeX, reading order), Windows pip install, PP-OCRv6 OCR (109 languages). Good fallback and the easiest "structure-first" option. |
| 4 | **Ollama + Vulkan** | Zero-effort to try (same engine as option 1, slower backend). Known crash reports on this exact GPU (Arc 140V) — treat as a smoke test, not the production path. |

**Not recommended**: Marker/surya (no Intel support, and Japanese accuracy is only ~86% — it would not fix the core problem), Tesseract (68% on printed Japanese, no structure), IPEX-LLM Ollama portable (repo archived, vision models crash-prone, Qwen2.5-VL unverified), cloud APIs (excluded: must be offline/free).

The single most important finding: **Qwen2.5-VL is the first model family that demonstrably fixes the Japanese error problem** (independent tests: ~94% kana accuracy, ~87% correct on mixed CJK pages vs HPD's ~80-85%), and it runs via llama.cpp on the user's exact GPU family (Lunar Lake iGPU is on llama.cpp's official SYCL-supported list).

---

## Hardware context (important correction)

The "Intel Arc 140V (16GB)" is **not** a discrete GPU with 16 GB VRAM. It is the **Lunar Lake (Core Ultra 200V) integrated GPU**: 8 Xe2 cores, 128 EU-equivalent, XMX matrix engines (~53-67 INT8 TOPS), sharing the system's LPDDR5X memory (up to ~136 GB/s class bandwidth, roughly 1/4 of an Arc A770's 560 GB/s GDDR6). The 16 GB is total system RAM shared with the CPU and NPU.

Consequences for model selection:

- A Qwen2.5-VL-7B Q4_K_M GGUF (~6.0 GB) + mmproj vision projector (~1.0-1.5 GB) + KV cache fits alongside a Windows OS in 16 GB — tight but workable.
- 32B-class models (21 GB Q4) do **not** fit; anything larger will spill to CPU and be impractical.
- iGPU bandwidth is the bottleneck for text generation; expect roughly 1/3 the token rate of a discrete Arc card on the same model.

---

## Comparison table

| Tool | Backend on this machine | Japanese quality (evidence) | Markdown structure | Speed estimate (per page) | Memory | Install effort | Verdict |
|------|-------------------------|------------------------------|--------------------|---------------------------|--------|----------------|---------|
| **llama.cpp SYCL + Qwen2.5-VL-7B** | SYCL (Intel oneAPI runtime, prebuilt zip) | Strong for printed text; ~94% kana, ~87% correct mixed CJK (independent tests); weak on handwriting/small text | Prompt-driven markdown (tables/headers OK, needs a good prompt); no layout model — reading order comes from the VLM | ~2-4 min/page (est.) | ~7.5 GB (6.0 + 1.5 mmproj + KV) | Low (unzip + pull GGUF) | **Recommended** |
| **Qwen2.5-VL-3B (same path)** | SYCL | Lower than 7B; reading-order errors in zero-shot tests; fine-tuned 3B OCR models (EN/ZH) are strong | Same as above | ~1-2 min/page (est.) | ~4 GB | Low | Test as fast variant |
| **PaddleOCR-VL 0.9B / 1.6** | CPU only (PaddlePaddle has no Intel GPU backend) | 109 languages incl. Japanese; SOTA claims on OmniDocBench (96.3% v1.6); same lineage as HPD but newer/stronger | Native markdown (page-level `doc-parser` pipeline outputs markdown/JSON) | ~60s/page (measured on Xeon via OpenVINO; estimate only) | ~2-4 GB | Low (paddleocr pip, already has Paddle stack) | Strong upgrade path over HPD |
| **MinerU v3.4** | CPU (pipeline backend), no Intel GPU | PP-OCRv6 OCR, 109 languages; ~11% OmniDocBench gain over PP-OCRv5 | Excellent: tables to HTML, formulas to LaTeX, reading order, headers/footers removal | ~30-90s/page CPU (estimate) | 4 GB min (GPU modes); 2 GB (hybrid-engine) | Low (pip) | Best "structure-first" CPU option |
| **Ollama (mainline) + Vulkan** | Vulkan | Same model quality as llama.cpp (same engine) | Same as llama.cpp | Slower than SYCL (~50-70% of SYCL speed) | Same as llama.cpp | Very low (`ollama run qwen2.5vl:7b`) | Smoke-test only; crashes reported on Arc 140V |
| **IPEX-LLM Ollama portable** | SYCL via Intel fork | Same models; Qwen2.5-VL **not** on verified list | Same | Good (SYCL) | Same | Low (zip + start-ollama.bat) | **Avoid**: repo archived 2026-01; vision-model crashes (#13293, #13318) |
| **Marker + surya-2** | CPU/llama.cpp (no Intel GPU) | surya-2 Japanese = **86.2%** (worse than HPD's effective ~85%; not a fix) | Native markdown/JSON/HTML | 5-10 min/page CPU (measured in spec 004 eval) | ~1-2 GB | High (llama-server + mmproj chain) | Not viable on this hardware; also doesn't fix Japanese accuracy |
| **Tesseract (jpn tessdata)** | CPU | Weak: ~68% printed, 41% handwriting, 53% vertical Japanese; needs PSM tuning + furigana removal | None (raw text; layout/table ~72%) | Seconds/page | <1 GB | Low (pip install pytesseract) | Cheap fallback only |
| **MiniCPM-V 4.6** | CPU/llama.cpp or Ollama (Vulkan) | 1.3B params, OCRBench ~ Qwen3.5-2B level; Japanese unverified | Prompt-driven | Fast (small model) | ~4 GB | Low | Quick experiment; no Japanese evidence |
| **Cloud APIs (Mathpix, Google Vision, Azure)** | n/a | Very good | Mathpix: excellent tables/LaTeX | Fast | n/a | n/a | **Excluded** (must be offline/free) — noted for completeness |

Speed estimates are marked as estimates: no public benchmark exists for this exact chip (Lunar Lake Arc 140V) with these models. Anchors used: user-measured 27 tok/s on qwen35-A3B MoE via SYCL on this GPU; llama.cpp SYCL on Arc A770 (Llama-7B Q4: 24.7 tok/s); SYCL-vs-Vulkan 2x gap; iGPU bandwidth ~1/3 of A770.

---

## 1. llama.cpp SYCL + Qwen2.5-VL (recommended)

### Support status (verified, primary sources)

- llama.cpp's SYCL backend officially supports Intel GPUs including **"Built-in Arc: Meteor Lake, Arrow Lake, Lunar Lake iGPUs"** — the user's Arc 140V (Lunar Lake) is on the supported list ([SYCL backend docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)).
- Windows install is a **prebuilt binary zip** (`llama-b*-bin-win-sycl-x64.zip`) that bundles the SYCL runtime — **no oneAPI toolkit install required** ([SYCL docs, Windows section](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)).
- Build notes: use the FP16 build (recommended for performance); oneDNN is the default GEMM; verified oneAPI release 2025.3.3 ([SYCL docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)).
- Qwen2.5-VL is supported by mainline llama.cpp (`Qwen2_5_VLForConditionalGeneration`, PR [#12595](https://github.com/ggml-org/llama.cpp/pull/12595)); run with `llama-server.exe -m model.gguf --mmproj mmproj-f16.gguf`. Ollama v0.30.11 also added "default Qwen2.5VL window-attention metadata in llama.cpp," confirming mainline support ([release notes](https://cloud.tencent.com.cn/developer/article/2699997), see also [llama.cpp PR #12595](https://github.com/ggml-org/llama.cpp/pull/12595)).
- SYCL is roughly **2x faster than Vulkan** on Intel Arc (benchmark on Qwen3-8B-Q4_K_M: SYCL 323/15.25 prefill/gen tok/s vs Vulkan 215.9/7.35; see [ollama PR #11160 discussion](https://github.com/ollama/ollama/pull/11160)). The same ~3x gap appears on Arc Pro B50 (35B MoE: Vulkan ~10 vs SYCL ~33 tok/s, [ollama issue #16930](https://github.com/ollama/ollama/issues/16930)).

### Why Qwen2.5-VL for Japanese

- CC-OCR multilingual benchmark (ICCV 2025): Qwen2.5-VL-72B scores **76.27 on Japanese**, the top generalist score ([CC-OCR paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Yang_CC-OCR_A_Comprehensive_and_Challenging_OCR_Benchmark_for_Evaluating_Large_ICCV_2025_paper.pdf)).
- Independent hands-on test of the 7B model on 32 real mixed CJK images: **87.5% fully correct on Chinese+Japanese pages, 83.3% on English+Japanese, ~94% kana accuracy** (vs 72% for the previous generation); remaining errors are kanji/simplified-Chinese confusion and small text (<8pt) being skipped; handwriting remains a weakness ([test write-up](https://blog.csdn.net/weixin_42627459/article/details/157524786)).
- Model sizes: 8B params BF16 (~16 GB) — must be quantized; Q4_K_M GGUF ~6.0 GB fits 16 GB shared memory ([model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct), [GGUF quants](https://huggingface.co/dekthedev/Qwen2.5-VL-3B-Instruct-GGUF), [mradermacher 7B quants](https://huggingface.co/mradermacher)).
- No XPU-specific support from Qwen, but none is needed — llama.cpp handles the hardware; the model card explicitly notes quantizations exist "to use this model in llama.cpp, Ollama, LM Studio, or any compatible app" ([model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)).

### Install steps (Windows)

1. Download `llama-b*-bin-win-sycl-x64.zip` from [llama.cpp releases](https://github.com/ggml-org/llama.cpp/releases); extract to e.g. `C:\tools\llama`.
2. Download Qwen2.5-VL-7B-Instruct GGUF (Q4_K_M, ~6 GB) + mmproj-f16 (~1.5 GB) from a maintained HF repo (e.g. [dekthedev/Qwen2.5-VL-3B-Instruct-GGUF](https://huggingface.co/dekthedev/Qwen2.5-VL-3B-Instruct-GGUF) pattern; 7B equivalents from [mradermacher](https://huggingface.co/mradermacher) / [DevQuasar GGUF](https://github.com/ggml-org/llama.cpp/pull/12595)).
3. Serve:
   ```
   llama-server.exe -m qwen25vl-7b-q4_k_m.gguf --mmproj qwen25vl-7b-mmproj-f16.gguf --host 127.0.0.1 --port 8080 -c 8192
   ```
4. Parse worker calls the OpenAI-compatible `/v1/chat/completions` endpoint with the page image + a markdown prompt (e.g. "Output the content of this textbook page as markdown. Preserve tables, headers, lists and furigana. Do not invent text.").
5. Expected: text gen ~10-20 tok/s on this iGPU; image encode + prefill of ~1500-2000 visual tokens dominates per-page time.

### Known risks

- First-load JIT compilation makes the first call slow (SYCL has no AOT) ([SYCL docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)).
- Vision + context memory: keep `-c` at 8k-16k; 16 GB shared RAM is the hard ceiling.
- Prompt engineering matters a lot for OCR quality (explicitly listing languages improved complete recognition 20% → 100% in one test ([test write-up](https://blog.csdn.net/weixin_42627459/article/details/157524786))).

---

## 2. Ollama (mainline) + Vulkan

### Verified status

- Official docs: "Additional GPU support on Windows and Linux is provided via Vulkan" — Intel guidance links are Linux-only; there is **no official SYCL backend in mainline Ollama** ([docs.ollama.com/gpu](https://docs.ollama.com/gpu)).
- A SYCL/oneAPI backend for Ollama remains an **open proposal** ([issue #16930](https://github.com/ollama/ollama/issues/16930)); earlier PRs were not merged; a draft PR validated Windows Intel GPU support but is not in releases ([issue #16930](https://github.com/ollama/ollama/issues/16930), [PR #11160](https://github.com/ollama/ollama/pull/11160)).
- qwen2.5vl is in the Ollama library: 3b (3.2 GB), 7b (6.0 GB), 32b (21 GB), 72b (49 GB); requires Ollama 0.7.0+ ([ollama.com/library/qwen2.5vl](https://ollama.com/library/qwen2.5vl)).

### Known problems on this exact GPU (Arc 140V)

- **Crash reports on Intel Arc 140V (iGPU, Vulkan)**: `EXCEPTION_ACCESS_VIOLATION` on first inference batch with qwen3.5, not fixed by coopmat/pipeline-cache workarounds ([issue #14610](https://github.com/ollama/ollama/issues/14610)).
- Ollama's Vulkan runner is **slower than llama.cpp's Vulkan** on Intel (sometimes slower than CPU) ([issue #13567](https://github.com/ollama/ollama/issues/13567)).
- Vulkan on Intel Arc is ~half of SYCL throughput ([PR #11160 discussion](https://github.com/ollama/ollama/pull/11160)).
- Newer versions moved GPU detection; users report needing `OLLAMA_IGPU_ENABLE=1` on Windows (previously `OLLAMA_VULKAN=1`) ([issue #16452](https://github.com/ollama/ollama/issues/16452)).
- Q4_K_M quantizations have produced gibberish/hangs on some Intel Arc cards under Vulkan (Q4_0/Q8_0 worked) ([issue #14978](https://github.com/ollama/ollama/issues/14978)).

**Verdict**: free to smoke-test (`ollama run qwen2.5vl:7b` after setting `OLLAMA_IGPU_ENABLE=1`), but don't build the pipeline on it. **LM Studio** (Vulkan backend, GUI, local OpenAI-compatible server on :1234) is a reasonable alternative smoke test — one Arc A770 user confirmed Qwen2.5-VL-32B ran correctly there while ipex-llm Ollama crashed ([issue #13293](https://github.com/intel/ipex-llm/issues/13293)); it shares llama.cpp's Vulkan performance profile, so expect the same ~50-70% of SYCL speed.

---

## 3. IPEX-LLM Ollama portable (Intel fork) — avoid

- Intel's Ollama fork with SYCL acceleration; portable zip runs `start-ollama.bat` with an Ollama-compatible API on 11434 ([IPEX-LLM repo](https://github.com/intel/ipex-llm)).
- **Repo archived (read-only) as of 2026-01-28** — no longer maintained.
- Qwen2.5-VL is **not** on the verified model list (Qwen-VL and Qwen2-VL are; 2.5-VL is not).
- Vision-model crashes on Windows Arc: Qwen2.5-VL-32B crash on Arc A770 ([#13293](https://github.com/intel/ipex-llm/issues/13293)); nil-pointer crash loading any vision model on multi-GPU Arc ([#13318](https://github.com/intel/ipex-llm/issues/13318)). Same hardware worked via Vulkan in LM Studio — the bugs are in the ipex-llm integration, not the GPU.
- The archived 2.3.0b20250725-win build is still downloadable and *might* work on a single-GPU laptop (the crashes were multi-GPU), but an archived, vision-unverified fork is a poor foundation.

---

## 4. PaddleOCR-VL — the "better HPD" (CPU-only on Intel)

- **PaddleOCR-VL** is PaddleOCR's document-parsing VLM: 0.9B params (NaViT-style dynamic-resolution visual encoder + ERNIE-4.5-0.3B LM), latest **v1.6** claims >96.3% on OmniDocBench v1.6; **supports 109 languages including Japanese** ([GitHub README](https://github.com/PaddlePaddle/PaddleOCR), [HF model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)).
- Deployment: PaddleOCR `doc-parser` pipeline (markdown/JSON output), vLLM serving, or transformers (element-level) ([HF model card](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)).
- **Critical caveat**: PaddlePaddle has **no Intel GPU backend**. Paddle's "XPU" means **Baidu Kunlun chips**, not Intel XPU ([Paddle hardware support](https://paddlepaddle-org-cn.bj.bcebos.com/documentation/docs/zh/guides/hardware_support/hardware_info_cn.html), [Kunlun install doc](https://www.paddlepaddle.org.cn/documentation/docs/en/2.4/install/install_Kunlun_en.html)); PyTorch's "xpu" (Intel GPU) is a different thing entirely. On this machine PaddleOCR-VL runs **CPU-only** (or via an OpenVINO port, e.g. [Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO](https://huggingface.co/Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO)).
- CPU speed reference: ~64s/page (PaddleOCR-VL-1.5, OpenVINO, Xeon Gold 6242, ~35 tok/s decode) — with the tester's caveat that it "probably isn't useful" as an absolute number ([OpenVINO port README](https://huggingface.co/Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO/blob/main/README.md)).
- Relationship to HPD: HPD-Parsing is PaddleOCR's high-throughput pipeline (also 1B-class); PaddleOCR-VL is the newer, SOTA-focused sibling ([GitHub README](https://github.com/PaddlePaddle/PaddleOCR)). It is the natural *architectural* upgrade of the existing stack: same install, same Python API, markdown out of the box — at CPU speed on this hardware.

---

## 5. MinerU — best CPU structure-first option

- MinerU v3.4 (2026-06-18): PDF/image/DOCX → markdown + JSON with layout analysis, tables → HTML, formulas → LaTeX, headers/footers removed, reading order ([official repo](https://github.com/opendatalab/MinerU)).
- Windows pip install supported (Python 3.10-3.12): `uv pip install -U "mineru[all]"`; pure-CPU supported via the `pipeline` backend (`mineru -p in.pdf -o out/ -b pipeline`); GPU modes need 4 GB (pipeline) / 8 GB (vlm-engine) / 2 GB (hybrid-engine) VRAM ([README](https://github.com/opendatalab/MinerU)).
- OCR: **PP-OCRv6** (upgraded in v3.4, ~11% OmniDocBench gain), "detection and recognition of 109 languages" including Japanese (Japanese is routed to the `ch` OCR model since v3.4) ([README](https://github.com/opendatalab/MinerU)).
- **No Intel GPU/XPU support** — acceleration is CUDA, MPS, Ascend NPU, and domestic Chinese AI chips; on this machine it runs CPU-only ([README](https://github.com/opendatalab/MinerU)).
- License note: "MinerU Open Source License, based on Apache 2.0 with additional conditions" since v3.1 (was AGPLv3) ([README](https://github.com/opendatalab/MinerU)).

**Verdict**: the best table/structure handling of the CPU options; Japanese accuracy rests on PP-OCRv6 (same Paddle lineage as HPD, newer and stronger). Good fallback; also useful as a ground-truth comparator in an A/B test against Qwen2.5-VL.

---

## 6. Marker + surya — re-verified, still not viable (and not the fix)

- Marker's OCR now uses **surya-2**, a 650M-param VLM; Japanese scores **86.2%** on its internal 91-language benchmark (Chinese 82.5%, English 92.3%) ([surya repo](https://github.com/VikParuchuri/surya)) — barely above HPD's effective ~85%; it would **not** fix the Japanese character problem.
- Backends: vLLM (NVIDIA-only) or llama.cpp (CPU/Apple Silicon). **No Intel GPU support** ([surya repo](https://github.com/VikParuchuri/surya)).
- Spec 004 measured 5-10 min/page CPU via llama.cpp — confirmed impractical ([specs/004-hybrid-parser/spec.md](file:///D:/LanguageNotebook/specs/004-hybrid-parser/spec.md)).
- Marker's `TableConverter` outputs json/markdown/html; surya outputs JSON only ([marker repo](https://github.com/datalab-to/marker), [surya repo](https://github.com/VikParuchuri/surya)).
- The user's observed 27 tok/s on qwen35 SSM layers via SYCL is consistent with llama.cpp SYCL performance on this iGPU class — i.e., even the "fast" path they tried is the SYCL ceiling, and the model choice (surya's Qwen3.5-based VLM) is the wrong fix for Japanese.

**Verdict**: leave archived. If VLM-based OCR is ever revisited, use Qwen2.5-VL directly (Section 1), not surya.

---

## 7. Tesseract — cheap fallback only

- Japanese supported via `jpn` tessdata (`--oem 3 --psm 6 -l jpn+eng`), integrates via pytesseract ([tessdata](https://github.com/tesseract-ocr/tessdata), [usage guide](https://developer.baidu.com/article/detail.html?id=3680409)).
- Measured quality (independent tests): **~68% on printed Japanese, ~41% handwriting, ~53% vertical text** — well below every DL option above; layout/table understanding ~70-72% ([benchmark card](https://huggingface.co/thelamapi/next-ocr-GGUF), [comparison article](https://developer.baidu.com/article/detail.html?id=3680409)).
- Furigana (small kana annotations — common in Japanese textbooks) actively hurts Tesseract: removing furigana improved CER by +5-11% ([furigana research paper](https://stefanheinrich.net/files/2022_Bjerregaard_arXiv.pdf)).
- No structure/markdown output; would need custom post-processing.

---

## 8. Quick notes on other models considered

- **MiniCPM-V 4.6**: 1.3B params (SigLIP2-400M + Qwen3.5-0.8B), ~4 GB VRAM (2 GB GGUF/CPU), **merged into Ollama's official library** — the fastest lightweight thing to try, but Japanese OCR quality is unverified (OCRBench at roughly Qwen3.5-2B level) ([MiniCPM-V repo](https://github.com/OpenBMB/MiniCPM-V)).
- **InternVL3-8B**: strong general doc OCR; Q4 GGUFs ~3.3-4.2 GB exist for llama.cpp, ~8 GB min for usable inference ([InternVL3-8B GGUF](https://huggingface.co/SandLogicTechnologies/Internvl3-8b-instruct-GGUF)). No Japanese-specific evidence found; no Intel-specific support beyond generic llama.cpp. Lower priority than Qwen2.5-VL given the Japanese requirement.
- **Cloud/API (Mathpix, Google Cloud Vision, Azure AI Document Intelligence)**: best-in-class Japanese accuracy and structure (especially Mathpix tables/LaTeX) but violates the offline/free constraint — excluded by requirement, noted for completeness.

---

## Recommended implementation plan

**Phase 1 — validate (half a day):**
1. Download llama.cpp SYCL Windows zip; serve Qwen2.5-VL-7B Q4_K_M + mmproj via `llama-server.exe`.
2. A/B test against current HPD on 10 pages of the Shinkanzen N3 scan: char error rate, table capture, page latency. Use a strict markdown prompt (see Section 1, Known risks). Also test the 3B variant for the speed/quality tradeoff.
3. If Ollama + Vulkan is preferred for ops simplicity, run the same A/B via `ollama run qwen2.5vl:7b` (with `OLLAMA_IGPU_ENABLE=1`, latest Ollama) — but expect the crash/slowness issues documented above; keep llama.cpp SYCL as the reference.

**Phase 2 — integrate (if quality holds):**
4. Add an `llm_vlm` routing branch in `parse_pdf_hybrid()` (per the parser interface contract in spec 004 — same signature, new `method_name`), using the OpenAI-compatible endpoint of `llama-server` for scanned PDFs; keep PyMuPDF for text-layer PDFs.
5. Page render at 150-200 DPI (Qwen2.5-VL handles full-page input; resize so long edge fits the model's resolution guidance; images divisible by 28/14).
6. Cache the model server as a sidecar process (like the old GPU worker pattern), not inside the Celery container.

**Phase 3 — fallbacks:**
7. If the VLM path underperforms: MinerU CPU pipeline (structure-first) or PaddleOCR-VL CPU (HPD-lineage upgrade) as the scanned-PDF default; Tesseract only as a last-resort CPU path.

---

## Sources

- [llama.cpp SYCL backend docs (supported GPUs incl. Lunar Lake iGPU; Windows prebuilt zips; FP16 build; oneDNN)](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md)
- [llama.cpp PR #12595 — Qwen2.5-VL support](https://github.com/ggml-org/llama.cpp/pull/12595)
- [Ollama hardware docs — Vulkan covers "additional GPU support on Windows and Linux"; Intel guidance Linux-only](https://docs.ollama.com/gpu)
- [Ollama issue #16930 — open SYCL backend proposal; Vulkan ~10 vs SYCL ~33 tok/s on Arc Pro B50](https://github.com/ollama/ollama/issues/16930)
- [Ollama PR #11160 — SYCL ~2x Vulkan on Intel Arc (prefill/gen 323/15.25 vs 215/7.35)](https://github.com/ollama/ollama/pull/11160)
- [Ollama issue #14610 — crashes on Intel Arc 140V iGPU Vulkan](https://github.com/ollama/ollama/issues/14610)
- [Ollama issue #13567 — Ollama Vulkan slower than llama.cpp Vulkan on Intel](https://github.com/ollama/ollama/issues/13567)
- [Ollama issue #16452 — OLLAMA_IGPU_ENABLE / GPU detection on Windows](https://github.com/ollama/ollama/issues/16452)
- [Ollama issue #14978 — Q4_K_M gibberish/hang on Intel Arc under Vulkan](https://github.com/ollama/ollama/issues/14978)
- [Ollama library qwen2.5vl (sizes; requires 0.7.0)](https://ollama.com/library/qwen2.5vl)
- [Qwen2.5-VL-7B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
- [CC-OCR (ICCV 2025) — Qwen2.5-VL-72B top Japanese score 76.27](https://openaccess.thecvf.com/content/ICCV2025/papers/Yang_CC-OCR_A_Comprehensive_and_Challenging_OCR_Benchmark_for_Evaluating_Large_ICCV_2025_paper.pdf)
- [Qwen2.5-VL-7B mixed CJK/Japanese hands-on test (~94% kana, ~87% mixed CJK)](https://blog.csdn.net/weixin_42627459/article/details/157524786)
- [Qwen2.5-VL GGUF quants + mmproj (llama.cpp usage examples)](https://huggingface.co/dekthedev/Qwen2.5-VL-3B-Instruct-GGUF)
- [PaddleOCR GitHub README (PaddleOCR-VL, 109 languages incl. Japanese, hardware backends)](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR-VL model card (0.9B, deployment paths, OmniDocBench claims)](https://huggingface.co/PaddlePaddle/PaddleOCR-VL)
- [PaddlePaddle hardware support (XPU = Baidu Kunlun)](https://paddlepaddle-org-cn.bj.bcebos.com/documentation/docs/zh/guides/hardware_support/hardware_info_cn.html)
- [PaddleOCR-VL-1.5 OpenVINO port — CPU ~64s/page on Xeon Gold 6242](https://huggingface.co/Echo9Zulu/PaddleOCR-VL-1.5-FP16-OpenVINO)
- [MinerU official repo (v3.4, Windows pip, backends, PP-OCRv6)](https://github.com/opendatalab/MinerU)
- [surya repo (surya-2 650M; Japanese 86.2%; backends vLLM/llama.cpp only)](https://github.com/VikParuchuri/surya)
- [marker repo](https://github.com/datalab-to/marker)
- [Tesseract Japanese quality comparison (68% printed / 41% handwriting / 53% vertical)](https://developer.baidu.com/article/detail.html?id=3680409)
- [Furigana impact on Tesseract Japanese OCR (paper)](https://stefanheinrich.net/files/2022_Bjerregaard_arXiv.pdf)
- [MiniCPM-V repo (4.6 = 1.3B, ~4 GB, in Ollama library)](https://github.com/OpenBMB/MiniCPM-V)
- [InternVL3-8B GGUF](https://huggingface.co/SandLogicTechnologies/Internvl3-8b-instruct-GGUF)
- [IPEX-LLM issues #13293 / #13318 (vision crash on Windows Arc; repo archived)](https://github.com/intel/ipex-llm/issues/13293)
- [Intel Arc 140V specifications (Lunar Lake iGPU, shared memory, XMX TOPS)](https://cputronic.com/en/gpu/intel-arc-140v)
- Repo specs: [003-marker-migration](file:///D:/LanguageNotebook/specs/003-marker-migration/spec.md), [004-hybrid-parser](file:///D:/LanguageNotebook/specs/004-hybrid-parser/spec.md)

---

*Verification note: all hardware-support claims above were checked against the cited primary sources (official docs/repos/issues), not assumed. No claims of "Intel Arc support" are made for any tool whose docs do not state it (PaddlePaddle, surya, vLLM, MinerU-GPU paths).*
