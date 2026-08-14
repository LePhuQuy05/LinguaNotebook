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

The model adapter lives in :mod:`src.services.slm_runtime` (shared with the
lesson-item generator): llama-cpp-python, CPU-only, lazy import — the suite
never imports it. Default model is Qwen3-1.7B Q4_K_M (Apache-2.0); path is
configurable via ``CURRICULUM_LLM_PATH``. See ``docs/curriculum-escalation.md``
for model choice and the one-line install.
"""

import logging
import re
from collections.abc import Sequence

from src.services.curriculum_service import Entry, Escalator
from src.services.hpd_markdown import split_pages
from src.services.slm_runtime import (
    get_runtime as _get_llm,
)
from src.services.slm_runtime import (
    resolve_model_file as _resolve_model_file,
)

logger = logging.getLogger(__name__)

# One entry per line, machine-checkable: <number>|<title>|<page>
_ENTRY_RE = re.compile(r"^\s*(\d{1,3})\s*\|\s*([^|\n]+?)\s*\|\s*(\d{1,4})\s*$")

# The model returns one entry per line; anything outside a couple of hundred
# entries (a book rarely has more) is a degenerate generation we truncate.
_MAX_ENTRIES = 200


def _build_prompt(markdown: str, toc_pages: set[int], known_pages: Sequence[int]) -> str:
    """Isolate the TOC pages and spell out the page whitelist.

    Only ``toc_pages`` content reaches the model — body pages are withheld so
    the model cannot silently copy a heading that is not on the TOC, and the
    whitelist is stated so the model (mostly) self-constrains. Verification in
    :func:`_verify_and_finalize` remains the hard guarantee.

    Two worked ``=>`` examples teach the 1.7B model the target line format; a
    small model mirrors the last few lines' shape, and without them it echoes
    the input TOC lines verbatim (``3課 人間関係 .....4``).
    """
    toc_content = "\n".join(body for n, body in split_pages(markdown) if n in toc_pages)
    allowed = ", ".join(str(p) for p in sorted(known_pages))
    return (
        "You are extracting the chapter table of contents from a scanned"
        " textbook's table-of-contents pages.\n"
        "Rewrite each TOC line as exactly one line: <number>|<title>|<page>,\n"
        "numbering the entries 1, 2, 3 ... in the order they appear.\n"
        f"Use ONLY page numbers from this list: {allowed}\n"
        "Do not explain, do not repeat. Output only the numbered lines.\n"
        "Examples:\n"
        "1課 あいさつ .....8\n=> 1|あいさつ|8\n"
        "2課 学校 .....30\n=> 2|学校|30\n\n"
        "--- TOC pages ---\n"
        f"{toc_content}\n\n"
        "Output:\n"
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
