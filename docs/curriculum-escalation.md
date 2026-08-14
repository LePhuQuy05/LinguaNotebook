# Optional SLM escalation for curriculum extraction

Feature 008, ticket 03/04. When a document's TOC is so mangled by OCR that the
rule-based scan cannot confirm it against the body (confidence below the
0.3 gate), the extractor may ask an **offline small-language model** to recover
the chapter map. This is strictly optional: with no model installed the app
behaves exactly as it did before the feature existed.

## How it works (the safety contract)

- **The model never sees the whole book.** It receives only the isolated TOC
  pages plus a list of **Known pages** — every page number the parse produced
  for the document.
- **A hallucinated page number is impossible.** The model must emit page
  numbers that are members of the Known-pages whitelist. Anything else is
  dropped at verification, in code, before anything is saved ("reason free,
  constrain late" — ADR-0001/0002).
- **Deterministic.** Sampling temperature is pinned to 0; results are parsed →
  validated → whitelist-checked → sorted → deduplicated → renumbered
  sequentially. Page ranges are always computed in code, never by the model.
- **Never blocks the parse.** Escalation runs inside the existing parse step
  via a thread executor, so model inference never stalls the worker's
  persistent event loop.

## Enable it (one documented step, 3 commands)

1. **Install the runtime** — the only extra dependency, and only when you want
   escalation (not in the base requirements):

   ```bash
   pip install llama-cpp-python
   ```

2. **Download a model** into the configured path. The default is
   `backend/model/curriculum-llm/` (already gitignored — `backend/model/` and
   `*.gguf` are in `.gitignore`). Any single `.gguf` file works; the resolver
   picks it up:

   ```bash
   # default model (fast on CPU):
   mkdir -p backend/model/curriculum-llm
   huggingface-cli download unsloth/Qwen3-1.7B-GGUF \
     Qwen3-1.7B-Q4_K_M.gguf --local-dir backend/model/curriculum-llm
   ```

3. **Restart the parse worker.** The worker imports the source at startup —
   without a restart the escalation is inert (see memory: *stale worker*).

The base install is unchanged: `pip install -r requirements.txt` does not pull
in `llama-cpp-python`, and a fresh clone with no model file runs identically to
before.

## Configuration

| Setting | Env var | Default |
| --- | --- | --- |
| Model file or dir | `CURRICULUM_LLM_PATH` | `./model/curriculum-llm` (relative to `backend/`) |

Set it in `backend/.env`:

```dotenv
CURRICULUM_LLM_PATH=./model/curriculum-llm
```

The path may point at a directory containing **exactly one** `.gguf`, or
directly at a `.gguf` file. An empty path, a path with no `.gguf`, or a
directory with several models resolves to "escalation disabled" — never a guess.

## Model choice

| Model | Quant | Size | When | License |
| --- | --- | --- | --- | --- |
| **Qwen3-1.7B-Instruct** (default) | Q4_K_M | ~1.1 GB | CPU speed | Apache-2.0 ✅ |
| **Qwen3-4B-Instruct** (accuracy option) | Q4_K_M | ~2.6 GB | better accuracy; non-thinking mode | Apache-2.0 ✅ |

**Excluded** — do not use these: `Qwen2.5-3B` and `Qwen2.5-VL-3B` are under the
**Qwen Research non-commercial license**, which the app must not ship as a
default. (Research, decision record, and license links:
`docs/research/curriculum-extraction-generalization.md`, ADR-0002.)

## Verify it works

- Parse a document whose TOC previously produced no map, then check
  `document_structures` rows appear (the worker logs
  `Saved N curriculum rows for document …`; escalation itself logs
  `Curriculum escalation: model … recovered N entries`).
- The unit test `tests/unit/test_curriculum_escalation.py` always runs; the
  real-model integration test `test_real_model_end_to_end` runs **only when a
  `.gguf` is configured** and skips otherwise.

## Implementation notes

- Module: `backend/src/services/curriculum_escalation.py` (lazy import of
  `llama_cpp` — importing the module never requires the package; the model is
  loaded once per process and cached).
- Trigger: `extract_curriculum(..., escalator=...)` in
  `backend/src/services/curriculum_service.py` — invoked below the
  `CONFIDENCE_LOW` (0.3) gate, and also when the TOC scan found
  chapter-looking lines but every dotted page anchor was mangled and both
  body fallbacks came up empty (the model still reads the real TOC pages).
- Wiring: `backend/src/workers/parse_worker.py::_save_curriculum_structure`
  builds the escalator and runs extraction through
  `loop.run_in_executor` so the persistent event loop is never blocked.
