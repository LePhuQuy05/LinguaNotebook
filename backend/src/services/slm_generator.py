"""Small-LM lesson item generator (feature 009, ticket 05).

The rule generator turns a single chunk into a single templated item. The
small-LM generator instead reads the whole chapter — every planned chunk, its
assigned content type, and the chapter title — and asks the model for one
schema-verified item per chunk, so questions are grounded in the chapter's
actual content and carry real answers.

Design ("reason free, constrain late", ADR-0001/0002):

- **Whole-chapter planning.** When the lesson orchestrator passes a chapter
  ``context`` (title + chunks + per-chunk types + a ``_cache``), the generator
  runs ONE model pass over the chapter and memoizes the parsed items in the
  cache; per-chunk calls then return their cached item. A chunk the model did
  not cover falls back to the rule generator.
- **Schema verification.** Output is strict JSON; each entry must match its
  item type's payload shape (four non-empty options, a valid integer
  ``correct_index``, the required keys) or it is dropped. ``correct_answer``
  is normalized to the text of the chosen option, so grading (by index) and
  the displayed answer always agree.
- **Graceful degradation.** No chapter context, no model file, malformed
  output, or an exception mid-inference → the rule generator for that chunk.
  With no model file configured every call is rule-only, indistinguishable
  from the rule-only setting.
"""

from __future__ import annotations

import asyncio
import json
import logging

from src.core.config import settings
from src.services.item_generators import GeneratedItem, RuleBasedGenerator
from src.services.slm_runtime import get_runtime, resolve_model_file

logger = logging.getLogger(__name__)

_ITEM_TYPES = {"flashcard", "reading", "grammar", "listening"}

# Required payload keys per item type. Option-bearing types must additionally
# have exactly four non-empty options and an integer correct_index in range.
_REQUIRED_KEYS = {
    "flashcard": {"term", "reading", "definition", "example"},
    "reading": {"passage", "options", "correct_index"},
    "grammar": {"pattern", "prompt", "options", "correct_index"},
    "listening": {"text", "audio_key", "options", "correct_index"},
}

# Per-passage JSON budget plus slack for the array wrapper: a chapter pass
# should finish in a bounded time, so the token cap grows with chapter size
# instead of letting a rambling model run to one huge cap (measured ~45 ch/s
# on CPU; a 10-passage chapter stays under a minute).
_LESSON_TOKENS_PER_PASSAGE = 150
_LESSON_TOKENS_MIN = 512


def _chunk_key(chunk: dict) -> str:
    return str(chunk.get("chunk_id") or "chunk")


class SlmGenerator:
    """The ``ItemGenerator`` that plans items across a whole chapter."""

    def __init__(self) -> None:
        self._fallback = RuleBasedGenerator()

    async def generate(
        self,
        chunk: dict,
        content_type: str,
        context: dict | None = None,
    ) -> list[GeneratedItem]:
        cache = (context or {}).get("_cache")
        if not isinstance(cache, dict):
            # Generic (no-chapter) call — the model has no chapter to read.
            return await self._fallback.generate(chunk, content_type)
        # A real `_cache` only exists inside a chapter context, so `context`
        # is non-None here (planning needs the title + planned chunks).
        assert context is not None
        if not cache.get("_planned"):
            await self._plan_chapter(cache, context)
        cached = cache.get(_chunk_key(chunk))
        if cached is None:
            return await self._fallback.generate(chunk, content_type)
        return cached

    async def _plan_chapter(self, cache: dict, context: dict) -> None:
        """Run the one whole-chapter model pass and memoize the result."""
        cache["_planned"] = True
        chunks = context.get("chunks") or []
        if not chunks:
            return
        model_path = resolve_model_file(settings.curriculum_llm_path)
        if model_path is None:
            return  # rule-only: no model configured
        plan = context.get("plan") or []
        prompt = _build_prompt(context.get("chapter_title", ""), chunks, plan)
        max_tokens = max(
            _LESSON_TOKENS_MIN,
            _LESSON_TOKENS_PER_PASSAGE * len(chunks),
        )
        try:
            runtime = get_runtime(model_path)
            # Model inference is CPU-bound and can take tens of seconds for a
            # whole chapter — run it in the default executor so a lesson
            # request never blocks the API's event loop (mirrors the
            # curriculum-escalation precedent in parse_worker).
            raw = await asyncio.to_thread(runtime.generate, prompt, max_tokens=max_tokens)
        except Exception:
            logger.exception("SLM lesson generation failed — falling back to rule")
            return
        for idx, item in _parse_items(raw).items():
            if 0 <= idx < len(chunks):
                cache[_chunk_key(chunks[idx])] = [item]


def _build_prompt(chapter_title: str, chunks: list, plan: list) -> str:
    """One model pass over the whole chapter.

    Each chunk is labelled with its assigned content type so the model makes
    the right kind of item (flashcard vs reading vs grammar vs listening).

    A two-passage worked example is essential: a 1.7B model mirrors the last
    few lines' shape, and without an example it echoes the ``[N] (type)``
    markers instead of emitting JSON (measured on Qwen3-1.7B).
    """
    passages = "\n".join(
        f"[{idx}] ({plan[idx] if idx < len(plan) else 'reading'})\n"
        f"{(chunk.get('content') or '').strip()}"
        for idx, chunk in enumerate(chunks)
    )
    return (
        "You are a Japanese textbook teacher writing study questions for the\n"
        f"chapter: {chapter_title or '(untitled)'}.\n"
        "Each numbered passage below is labelled with the kind of question to\n"
        "write:\n"
        "(flashcard) vocabulary card: term, reading (kana), definition in\n"
        'English, example sentence ("" if none)\n'
        "(reading) comprehension multiple choice: four plausible options, one\n"
        "correct\n"
        "(grammar) sentence-fill multiple choice: four plausible options, one\n"
        "correct\n"
        "(listening) comprehension multiple choice: four plausible options, one\n"
        "correct\n"
        '"correct_answer" is the exact text of the correct option (for a\n'
        "flashcard, the definition).\n"
        "Output ONE JSON array, one object per passage, in order.\n"
        'Each object: {"passage_index":N,"item_type":"...","question":"...",'
        '"correct_answer":"...","data":{...}}\n'
        "Example:\n"
        "[0] (flashcard)\n家族（かぞく）— family\n"
        "[1] (reading)\n学校に行きます。\n"
        '=> [{"passage_index":0,"item_type":"flashcard","question":"What does this term mean?",'
        '"correct_answer":"family","data":{"term":"家族","reading":"かぞく",'
        '"definition":"family","example":""}},'
        '{"passage_index":1,"item_type":"reading","question":"What is the main idea?",'
        '"correct_answer":"goes to school","data":{"passage":"学校に行きます。",'
        '"options":["goes to school","stays home","sleeps","eats"],"correct_index":0}}]\n'
        "Do not explain, do not repeat the passages. Output only the JSON array.\n\n"
        "--- Passages ---\n" + passages + "\n\nOutput JSON:\n"
    )


def _parse_items(raw: str) -> dict[int, GeneratedItem]:
    """Schema-verify the model's JSON into passage_index → item.

    The model may emit one combined array or (mirroring a single-passage
    example) one array per passage; every embedded JSON array is parsed and
    its entries merged by passage_index. Malformed output and entries that
    violate a type's schema are dropped; a chunk with no surviving entry
    falls back to the rule generator.
    """
    text = _strip_code_fence(raw)
    items: dict[int, GeneratedItem] = {}
    for array in _extract_json_arrays(text):
        for entry in array:
            if not isinstance(entry, dict):
                continue
            idx = entry.get("passage_index")
            item = _verify_entry(entry)
            if not isinstance(idx, int) or idx < 0 or item is None:
                continue
            items[idx] = item
    return items


def _extract_json_arrays(text: str) -> list[list]:
    """Every JSON array embedded in ``text``, parsed independently.

    A balanced scan (string literals respected) finds real arrays and ignores
    the ``[N] (type)`` passage markers and any trailing commentary, so the
    parse is robust to the exact shape of the model's output.
    """
    arrays: list[list] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] == "[":
            end = _match_bracket(text, i)
            if end is None:
                i += 1
                continue
            try:
                parsed = json.loads(text[i:end])
            except json.JSONDecodeError:
                pass  # e.g. the "[0]" passage marker, not a JSON array
            else:
                if isinstance(parsed, list):
                    arrays.append(parsed)
            i = end
            continue
        i += 1
    return arrays


def _match_bracket(text: str, start: int) -> int | None:
    """Index just past the ``]`` matching the ``[`` at ``start``, or None.

    Tracks string literals so a ``]`` inside a string (e.g. an option text)
    does not close the array early.
    """
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
    return None


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def _verify_entry(entry: dict) -> GeneratedItem | None:
    """Validate one model entry; return the item or ``None`` when out of schema."""
    item_type = entry.get("item_type")
    if item_type not in _ITEM_TYPES:
        return None
    data = entry.get("data")
    if not isinstance(data, dict) or not _REQUIRED_KEYS[item_type] <= set(data):
        return None
    if "options" in data:
        options = data["options"]
        if (
            not isinstance(options, list)
            or len(options) != 4
            or not all(isinstance(o, str) and o.strip() for o in options)
        ):
            return None
        correct_index = data["correct_index"]
        if not isinstance(correct_index, int) or not 0 <= correct_index < 4:
            return None
        correct_answer = options[correct_index]
    else:
        correct_answer = entry.get("correct_answer")
    question = entry.get("question")
    if not isinstance(question, str) or not question.strip():
        return None
    if not isinstance(correct_answer, str) or not correct_answer.strip():
        return None
    return GeneratedItem(
        item_type=item_type,
        question=question,
        correct_answer=correct_answer,
        payload=data,
    )
