"""Optional small-LM escalation for curriculum extraction (spec 008, ticket 03).

The rule scan in :mod:`src.services.curriculum_service` is conservative and
cheap, but a TOC the OCR mangled hard can fall below the confidence gate and
yield no map. This module layers an optional offline small-language-model pass
on top of it:

- **It never sees the whole book.** The prompt feeds only the isolated TOC
  pages plus the Known-pages whitelist (every page number the parse produced).
- **A hallucinated page number is impossible.** The model must emit page
  numbers from the whitelist; anything else is dropped at verification
  ("reason free, constrain late", ADR-0001/0002).
- **Deterministic.** Sampling temperature is pinned to 0; titles are renumbered
  monotonically and deduplicated.
- **Graceful degradation (ticket 04).** No model file configured → the builder
  returns ``None`` and extraction behaves exactly as before the feature
  existed.

The model adapter wraps llama-cpp-python (CPU-only, lazy import — the suite
never imports it). Default model is Qwen3-1.7B Q4_K_M (Apache-2.0); path is
configurable via ``CURRICULUM_LLM_PATH``. See ``docs/curriculum-escalation.md``
for model choice and the one-line install.
"""

import logging
import re
from collections.abc import Sequence

from src.services.curriculum_service import Entry, Escalator
from src.services.hpd_markdown import split_pages

logger = logging.getLogger(__name__)

# One entry per line, machine-checkable: <number>|<title>|<page>
_ENTRY_RE = re.compile(r"^\s*(\d{1,3})\s*\|\s*([^|\n]+?)\s*\|\s*(\d{1,4})\s*$")

# The model returns one entry per line; anything outside a couple of hundred
# entries (a book rarely has more) is a degenerate generation we truncate.
_MAX_ENTRIES = 200

# Adapter knobs — pinned for deterministic recovery (temperature 0; see
# ADR-0001 "reason free, constrain late"). Context 2048 comfortably covers a
# few TOC pages' worth of text; two threads keep CPU inference from starving
# the rest of the worker process.
_CTX = 2048
_THREADS = 2
_MAX_TOKENS = 512
_STOP_SEQ = ["\n\n"]


def _resolve_model_file(path: str) -> str | None:
    """Resolve ``CURRICULUM_LLM_PATH`` to a .gguf file.

    Accepts either a direct file path or a directory containing exactly one
    .gguf. Returns ``None`` when the path is empty/unresolvable (escalation
    disabled) or ambiguous (multiple models in the directory).
    """
    if not path:
        return None
    from pathlib import Path

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


def _build_prompt(markdown: str, toc_pages: set[int], known_pages: Sequence[int]) -> str:
    """Isolate the TOC pages and spell out the page whitelist.

    Only ``toc_pages`` content reaches the model — body pages are withheld so
    the model cannot silently copy a heading that is not on the TOC, and the
    whitelist is stated so the model (mostly) self-constrains. Verification in
    :func:`_verify_and_finalize` remains the hard guarantee.
    """
    toc_content = "\n".join(body for n, body in split_pages(markdown) if n in toc_pages)
    allowed = ", ".join(str(p) for p in sorted(known_pages))
    return (
        "You are extracting the chapter/lesson table of contents from a scanned"
        " textbook's table-of-contents pages.\n"
        "Output every entry as one line: <number>|<title>|<page>\n"
        f"Use ONLY page numbers from this list: {allowed}\n"
        "Follow the order the entries appear in the book. No preamble, no\n"
        "commentary, nothing else.\n\n"
        "--- TOC pages ---\n"
        f"{toc_content}"
    )


def _verify_and_finalize(raw: str | None, known_pages: Sequence[int]) -> list[Entry]:
    """Turn the model's raw output into verified, ordered ``Entry`` rows.

    Every emitted page must be a member of ``known_pages`` — the whitelist is
    the hard constraint that makes a hallucinated page number impossible.
    Entries are sorted by page, deduplicated on (title, page), and renumbered
    monotonically 1..N (the model's own numbering is trusted only as a hint).
    Rows are built once, never mutated: the numbering is applied at
    construction, not by rewriting an in-place placeholder.
    """
    known = set(known_pages)
    pairs: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    if not raw:
        return []
    for line in raw.splitlines():
        if len(pairs) >= _MAX_ENTRIES:
            break
        match = _ENTRY_RE.match(line)
        if not match:
            continue  # preamble, trailing noise, malformed line
        title = match.group(2).strip()
        page = int(match.group(3))
        if page not in known:
            continue  # hallucinated page → dropped, never a map row
        key = (title, page)
        if key in seen:
            continue
        seen.add(key)
        pairs.append((title, page))

    pairs.sort(key=lambda p: (p[1], p[0]))
    return [
        {"part": "", "chapter_num": i, "chapter_title": title, "page": page}
        for i, (title, page) in enumerate(pairs, start=1)
    ]


class _CurriculumLLM:
    """Thin lazy adapter over llama-cpp-python (CPU-only inference)."""

    def __init__(self, model_path: str) -> None:
        # Lazy import: this is an optional dependency and the module must be
        # importable in environments that never run escalation.
        from llama_cpp import Llama

        self._llm = Llama(
            model_path=model_path,
            n_ctx=_CTX,
            n_threads=_THREADS,
            verbose=False,
        )

    def generate(self, prompt: str) -> str:
        out = self._llm(
            prompt,
            temperature=0.0,
            max_tokens=_MAX_TOKENS,
            stop=_STOP_SEQ,
        )
        # llama-cpp's return is untyped; normalize through str() so the
        # signature stays a definite str under --strict.
        choices = out.get("choices", [])
        text = choices[0].get("text", "") if choices else ""
        return str(text)


# Process-level cache: the model is a few hundred MB and takes seconds to load;
# load once and reuse across documents in the same worker process.
_llm_cache: dict[str, _CurriculumLLM] = {}


def _get_llm(model_path: str) -> _CurriculumLLM:
    llm = _llm_cache.get(model_path)
    if llm is None:
        llm = _CurriculumLLM(model_path)
        _llm_cache[model_path] = llm
    return llm


def build_curriculum_escalator() -> Escalator | None:
    """Build the escalator from configuration, or ``None`` to disable it.

    ``None`` when no model is configured or resolvable — the caller (parse
    worker) then behaves exactly as if the feature never existed.
    """
    from src.core.config import settings

    model_path = _resolve_model_file(settings.curriculum_llm_path)
    if model_path is None:
        return None

    def escalate(markdown: str, toc_pages: set[int], known_pages: list[int]) -> list[Entry]:
        prompt = _build_prompt(markdown, toc_pages, known_pages)
        raw = _get_llm(model_path).generate(prompt)
        entries = _verify_and_finalize(raw, known_pages)
        logger.info(
            "Curriculum escalation: model %s recovered %d entries (toc_pages=%d known_pages=%d)",
            model_path,
            len(entries),
            len(toc_pages),
            len(known_pages),
        )
        return entries

    return escalate
