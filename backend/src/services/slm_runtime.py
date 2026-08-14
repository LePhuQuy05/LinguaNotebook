"""Shared offline small-LM runtime (llama-cpp-python, CPU-only).

Both the curriculum escalator (spec 008) and the lesson-item generator
(feature 009) run the same GGUF model through llama-cpp-python. This module
owns the lazy adapter, the .gguf resolver, and the process-level model cache,
so the model loads exactly once per worker process and both callers share it.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Adapter knobs — pinned for deterministic recovery (temperature 0; see
# ADR-0001 "reason free, constrain late"). Context 2048 comfortably covers a
# few TOC pages or one lesson chapter; two threads keep CPU inference from
# starving the rest of the worker process.
_CTX = 2048
_THREADS = 2
_MAX_TOKENS = 512
_STOP_SEQ = ["\n\n"]


def resolve_model_file(path: str) -> str | None:
    """Resolve a model path to a .gguf file, or ``None`` to disable.

    Accepts either a direct file path or a directory containing exactly one
    .gguf. ``None`` when the path is empty/unresolvable (runtime disabled)
    or ambiguous (multiple models in the directory).
    """
    if not path:
        return None
    p = Path(path)
    if p.is_file() and p.suffix.lower() == ".gguf":
        return str(p)
    if p.is_dir():
        ggufs = sorted(f for f in p.iterdir() if f.suffix.lower() == ".gguf")
        if len(ggufs) == 1:
            return str(ggufs[0])
        if len(ggufs) > 1:
            return None  # ambiguous — refuse to guess
    return None


class SlmRuntime:
    """Thin lazy adapter over llama-cpp-python (CPU-only inference).

    The ``llama_cpp`` import is deferred to ``__init__`` so this module stays
    importable in environments that never run a model (and the test suite
    never imports it).
    """

    def __init__(self, model_path: str) -> None:
        from llama_cpp import Llama

        self._llm = Llama(
            model_path=model_path,
            n_ctx=_CTX,
            n_threads=_THREADS,
            verbose=False,
        )

    def generate(self, prompt: str, max_tokens: int = _MAX_TOKENS) -> str:
        out = self._llm(
            prompt,
            temperature=0.0,
            max_tokens=max_tokens,
            stop=_STOP_SEQ,
        )
        # llama-cpp's return is untyped; normalize through str() so the
        # signature stays a definite str under --strict.
        choices = out.get("choices", [])
        text = choices[0].get("text", "") if choices else ""
        return str(text)


# Process-level cache: the model is a few hundred MB and takes seconds to
# load; load once per process and reuse across callers and documents.
_runtime_cache: dict[str, SlmRuntime] = {}


def get_runtime(model_path: str) -> SlmRuntime:
    runtime = _runtime_cache.get(model_path)
    if runtime is None:
        runtime = SlmRuntime(model_path)
        _runtime_cache[model_path] = runtime
    return runtime
