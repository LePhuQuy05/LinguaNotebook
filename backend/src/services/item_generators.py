"""Lesson item generators — a knowledge chunk becomes a structured item.

Feature 009 (ticket 01): a single swappable seam behind which lesson
items are produced. `ItemGenerator` is the protocol; `RuleBasedGenerator`
is the deterministic, always-on floor. The offline SLM generator
(ticket 05) implements the same protocol behind the same dispatcher,
selected by the LESSON_GENERATOR setting (default: "rule").

Structured per-type payloads (stored in the item's `data` column):

  flashcard  {term, reading, definition, example}
  reading    {passage, options[4], correct_index}
  grammar    {pattern, prompt, options[4], correct_index}
  listening  {text, audio_key, options[4], correct_index}

`question` and `correct_answer` stay rendered strings so old items
(no `data`) keep working.
"""

from __future__ import annotations

import logging
import random
import re
import zlib
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from src.core.config import settings

logger = logging.getLogger(__name__)

# Deterministic distractor pool for grammar fill-in items: the correct
# particle plus three common alternatives make the four choices.
GRAMMAR_PARTICLES = ("が", "を", "に", "へ", "で", "と", "から", "まで", "の")

# Fixed fillers used to guarantee four options when a chunk does not
# yield enough real distractors.
FALLBACK_DISTRACTORS = ("None of the above", "All of the above", "Cannot be determined")

# A known particle directly after a noun run (kanji/kana), e.g. 学校に.
_PARTICLE_RE = re.compile(r"[一-龠ぁ-んァ-ヶ]+(が|を|に|へ|で|と|から|まで|の)")

# Textbook vocabulary entry shapes, tried in order: term（reading）—
# definition, then term — definition.
_VOCAB_ENTRY = (
    re.compile(
        r"^\s*([^\s（()]+?)\s*[（(]\s*([^（）()]+?)\s*[）)]\s*[—―\-–:：]\s*(.+?)\s*$"
    ),
    re.compile(r"^\s*([^\s—―\-–]+?)\s*[—―\-–]\s*(.+?)\s*$"),
)

# Content type → item type. Unknown types degrade to the flashcard (the
# safe default) so `ItemType()` in the lesson service never sees an
# invalid value.
_CONTENT_TYPE_TO_ITEM_TYPE = {
    "vocabulary": "flashcard",
    "reading": "reading",
    "grammar": "grammar",
    "listening": "listening",
}


@dataclass(frozen=True)
class GeneratedItem:
    """A structured item produced by a generator.

    `item_type` is a LessonItem.ItemType value (flashcard, reading,
    grammar, listening). `payload` becomes the item's JSON `data`
    column; `question` and `correct_answer` are the rendered strings.
    """

    item_type: str
    question: str
    correct_answer: str
    payload: dict


@runtime_checkable
class ItemGenerator(Protocol):
    """Build zero or one structured item from a knowledge chunk."""

    def generate(
        self,
        chunk: dict,
        content_type: str,
        context: dict | None = None,
    ) -> list[GeneratedItem]:
        """Return items for the chunk; [] skips it (e.g. empty content)."""
        ...


def _split_sentences(content: str) -> list[str]:
    """Split text into sentences on 。！？ keeping the terminator."""
    parts = [p.strip() for p in re.split(r"(?<=[。！？])", content)]
    return [p for p in parts if p]


def _shuffled(pool: list[str], key: str) -> list[str]:
    """Shuffle deterministically from a stable hash of `key`.

    The same chunk content always yields the same option order, so
    generated lessons are reproducible run-to-run (and tests are stable)
    without pinning the correct option to a fixed position.
    """
    rng = random.Random(zlib.crc32(key.encode("utf-8")))
    rng.shuffle(pool)
    return pool


def _four_options(
    correct: str, distractors: list[str], key: str
) -> tuple[list[str], int]:
    """Return (four options, index of the correct one) for a chunk."""
    pool = [correct] + [d for d in distractors if d and d != correct]
    for filler in FALLBACK_DISTRACTORS:
        if len(pool) >= 4:
            break
        if filler not in pool:
            pool.append(filler)
    # Extremely short content with exhausted fillers: name the options.
    while len(pool) < 4:
        pool.append(f"Option {len(pool)}")
    options = _shuffled(pool, key)
    return options, options.index(correct)


def _particle_options(particle: str, key: str) -> tuple[list[str], int]:
    """Four-particle choices for a grammar fill-in item."""
    pool = [particle] + [p for p in GRAMMAR_PARTICLES if p != particle][:3]
    options = _shuffled(pool, key)
    return options, options.index(particle)


def _find_particle(content: str) -> str | None:
    """The first known particle directly after a noun run, or None."""
    m = _PARTICLE_RE.search(content)
    return m.group(1) if m else None


def _blank_particle(content: str, particle: str) -> str:
    """Replace the particle after the first noun run with ___."""
    return re.sub(r"(?<=[一-龠ぁ-んァ-ヶ])" + re.escape(particle), "___", content, count=1)


def _parse_vocab_entry(content: str) -> tuple[str, str, str, str] | None:
    """Parse a vocabulary entry into (term, reading, definition, example).

    Supports `term（reading）— definition` and `term — definition` lines
    plus simple `| term | reading | definition |` table rows. The entry
    lives on the first line; any following line becomes the example.
    """
    stripped = content.strip()
    if stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] and cells[2]:
            return cells[0], cells[1], cells[2], ""
    lines = stripped.splitlines()
    if not lines:
        return None
    first = lines[0].strip()
    example = " ".join(line.strip() for line in lines[1:] if line.strip())
    for pattern in _VOCAB_ENTRY:
        m = pattern.match(first)
        if not m:
            continue
        groups = m.groups()
        if len(groups) == 3:
            term, reading, definition = groups
        else:
            term, definition = groups
            reading = ""
        if term and definition:
            return term, reading, definition, example
    return None


class RuleBasedGenerator:
    """Deterministic generator: parse structure out of the chunk text.

    Vocabulary chunks that look like textbook entries become real
    flashcards (term/reading/definition/example); plain chunks become a
    flashcard carrying the whole chunk. Reading, grammar and listening
    chunks become four-option multiple-choice items; grammar first tries
    a particle fill-in, degrading to a sentence-choice item when no
    particle is found. An empty chunk is skipped.
    """

    def generate(
        self,
        chunk: dict,
        content_type: str,
        context: dict | None = None,
    ) -> list[GeneratedItem]:
        content = (chunk.get("content") or "").strip()
        if not content:
            return []
        item_type = _CONTENT_TYPE_TO_ITEM_TYPE.get(content_type, "flashcard")
        if item_type == "flashcard":
            return [self._flashcard(content)]
        return [self._multiple_choice(content, item_type)]

    def _flashcard(self, content: str) -> GeneratedItem:
        parsed = _parse_vocab_entry(content)
        if parsed:
            term, reading, definition, example = parsed
        else:
            term, reading, definition, example = content, "", "", ""
        return GeneratedItem(
            item_type="flashcard",
            question="What does this term mean?",
            correct_answer=definition or term,
            payload={
                "term": term,
                "reading": reading,
                "definition": definition,
                "example": example,
            },
        )

    def _multiple_choice(self, content: str, item_type: str) -> GeneratedItem:
        sentences = _split_sentences(content)
        lead = sentences[0] if sentences else content
        distractors = sentences[1:]

        if item_type == "grammar":
            particle = _find_particle(content)
            if particle is not None:
                options, correct_index = _particle_options(particle, content)
                correct_answer = particle
                question = "Complete the sentence using the correct particle"
                payload = {
                    "pattern": particle,
                    "prompt": _blank_particle(content, particle),
                    "options": options,
                    "correct_index": correct_index,
                }
            else:
                options, correct_index = _four_options(lead, distractors, content)
                correct_answer = lead
                question = "Complete the sentence using the correct form"
                payload = {
                    "pattern": "",
                    "prompt": content,
                    "options": options,
                    "correct_index": correct_index,
                }
        elif item_type == "reading":
            options, correct_index = _four_options(lead, distractors, content)
            correct_answer = lead
            question = "What is the main idea of this passage?"
            payload = {
                "passage": content,
                "options": options,
                "correct_index": correct_index,
            }
        else:  # listening
            options, correct_index = _four_options(lead, distractors, content)
            correct_answer = lead
            question = "Listen to the passage and answer: what is the topic?"
            payload = {
                "text": content,
                "audio_key": "",  # TTS asset, wired by ticket 02
                "options": options,
                "correct_index": correct_index,
            }

        return GeneratedItem(
            item_type=item_type,
            question=question,
            correct_answer=correct_answer,
            payload=payload,
        )


def get_item_generator() -> ItemGenerator:
    """Resolve the active generator from the LESSON_GENERATOR setting.

    "rule" (the default) → the rule-based floor. "slm"/"both" are not
    implemented until ticket 05; until then they degrade to the rule
    floor so behaviour is identical to rule-only.
    """
    requested = (settings.lesson_generator or "rule").strip().lower()
    if requested != "rule":
        logger.warning(
            "Lesson generator %r not implemented — falling back to rule", requested
        )
    return RuleBasedGenerator()
