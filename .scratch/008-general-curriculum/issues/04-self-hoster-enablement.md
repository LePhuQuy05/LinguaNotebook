# 04 — Self-hoster enablement + graceful degradation

**What to build:** A self-hoster can enable the SLM escalation with one documented step: a one-line optional install of the runtime plus placing a model file at the configured path. The base install is unchanged (no new required dependency); without a model the app behaves exactly as today. The model directory is gitignored; the model choice (Qwen3-1.7B Q4 default, 4B optional) is documented, including the license note.

**Blocked by:** 03 — documents/installs the adapter written there.

**Status:** done

- [x] One-line optional install documented (not in the base requirements)
- [x] Model path configurable; model directory gitignored; absent model → graceful degradation
- [x] Default model (Qwen3-1.7B Q4, Apache-2.0) and the accuracy option (4B) documented, with the non-commercial-license warning for excluded models
- [x] Gated real-model integration test runs when a model file is present, skips otherwise

## Comments

Implemented 2026-08-14. Enablement guide: `docs/curriculum-escalation.md`
(pip install `llama-cpp-python` → `huggingface-cli download
unsloth/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf` into `backend/model/curriculum-llm/`
→ restart worker). Config: `CURRICULUM_LLM_PATH` (pydantic-settings, default
`./model/curriculum-llm`), gitignored via existing `backend/model/` + `*.gguf`
rules. Escalation resolves to `None` when no `.gguf` is found → identical
behaviour. Gated integration test `test_real_model_end_to_end` skips unless a
model is configured.
