# 009 — Real lessons: structured items, generator seam, SRS loop, A/B compare

**Status:** ready-for-agent

## Problem Statement

A lesson today is barely connected to the book it came from. Every retrieved knowledge chunk becomes a "What does this term mean?" question whose answer is the whole paragraph; completing a lesson computes a score but never feeds retention (no SRS card is created); due SRS reviews only ever appear in the fallback generic path, never in chapter lessons; nothing generates lessons on schedule (the nightly task is a stub); and there is no way to see whether a rule-built or model-built item is actually better.

## Solution

From the user's perspective: a daily lesson is made of **real items** — vocabulary flashcards (term, reading, definition, example), and reading, grammar-fill, and listening questions as JLPT-style 4-option multiple choice — each generated from a knowledge chunk, each citing its source pages. Answering a recall-able item writes to the spaced-repetition deck; due reviews appear at the top of every lesson; and a scheduled task pre-generates tomorrow's lesson. A **lesson generator** seam lets items be built by a deterministic rule-based generator (always on) and/or an optional offline small-LM generator (CPU-only). A `LESSON_GENERATOR` setting picks the mode, and `both` produces two comparable lessons so the user can experience both and choose which generator to keep.

## User Stories

1. As a learner, I want a vocabulary item to be a flashcard with the term, its reading, its definition, and an example sentence, so that I can recall rather than read a paragraph.
2. As a learner, I want a reading item to show the passage, ask a comprehension question, and give four answer options, so that I practice understanding in JLPT style.
3. As a learner, I want a grammar item to show a pattern with a fill-in-the-blank sentence and four options, so that I practice sentential grammar.
4. As a learner, I want a listening item to play an audio clip and ask a four-option comprehension question, so that I practice listening with a transcript available.
5. As a learner, I want each item to cite its source pages so that I can open the book at the exact passage when I want more.
6. As a learner, I want every lesson to start with the SRS reviews that are due today (up to 30% of the lesson), so that retention is maintained before new material.
7. As a learner, I want answering an item to record the outcome immediately, so that a crash mid-lesson does not lose my review progress.
8. As a learner, I want vocabulary and grammar items to become SRS cards when answered, so that I meet them again on the spaced schedule.
9. As a learner, I want a correct/incorrect multiple-choice answer and a self-rated flashcard to both drive the SRS interval correctly.
10. As a learner, I want a lesson to be waiting for me at my scheduled time without my having to visit the app, so that the daily rhythm is automatic.
11. As a learner, I want to switch between the rule-built and model-built versions of the same lesson and complete the one I prefer, so that I can choose which generator to keep.
12. As a self-hoster, I want the rule-based generator to work with no model installed, so that the offline-first install stays small.
13. As a self-hoster, I want the small-LM generator to run offline on the CPU with the same model file the curriculum escalation already uses, so that there is no new dependency surface.
14. As a developer, I want the rule and small-LM generators behind one interface, so that each is testable in isolation and swappable via configuration.
15. As a learner, I want a lesson whose generation yields nothing usable to fall back to the existing generic lesson, so that I never get an empty lesson.
16. As a developer, I want old lesson items (without the structured payload) to keep rendering, so that existing data is not broken by the schema change.
17. As a learner, I want listening items to have their audio generated at lesson time, so that the item is complete when I open it.
18. As a learner, I want multiple-choice evaluation to be exact (selecting the correct option), so that grading is fair and predictable.

## Implementation Decisions

### Item model

- `lesson_items` gains one nullable JSON **`data`** column holding the structured per-type payload. `question` and `correct_answer` remain rendered strings (display + evaluation); old rows without `data` keep working (the UI falls back to today's rendering).
- Per-type payloads: **flashcard** `{term, reading, definition, example}`; **reading** `{passage, options[4], correct_index}`; **grammar** `{pattern, prompt, options[4], correct_index}`; **listening** `{text, audio_key, options[4], correct_index}`.

### Lesson generator seam (new)

- A protocol `ItemGenerator.generate(chunk, content_type, context) -> list[GeneratedItem]`, producing at most one item per chunk. `GeneratedItem` carries `item_type`, `question`, `correct_answer`, and the `data` payload.
- `RuleBasedGenerator`: deterministic, template + light-extraction (term/definition from a vocabulary chunk, a candidate sentence for grammar, etc.). Always available, unit-testable, cheap — the floor.
- `SlmGenerator`: optional, offline, CPU-only. Same signature; prompt → JSON → schema-verified output before anything is saved ("reason free, constrain late", matching the curriculum-escalation pattern and model choice). An error or empty result falls back to the rule generator for that chunk.
- Dispatcher `get_item_generator()` selects by the `LESSON_GENERATOR` setting (`rule | slm | both`); the default is `rule`.
- The orchestrator assigns `content_type` round-robin from the schedule (as today), routes each retrieved chunk through the selected generator, and **skips** chunks that yield no item; if the whole lesson yields nothing it falls back to the existing generic lesson.

### SRS loop

- **Write-back is per-answer** in `answer_item`: recall-able items (flashcard, grammar) call `srs_service.create_card(front, back, segment_id=item.knowledge_segment_id)`.
- **Recall-only deck** (ADR-0003): flashcard and grammar create cards; reading and listening are in-lesson comprehension and never enter the deck.
- Grading: flashcard self-rating (1–5) maps directly to the SM-2 score; grammar multiple-choice maps correct → 4, incorrect → 1.
- **Review slots**: every lesson (chapter and generic) reserves up to 30% of `daily_item_count` for due SRS cards (`get_due_cards`), surfaced review-first as flashcard-style items. `lesson_items` gains a nullable **`srs_card_id`** so answering a review routes to `rate_card`. Pacing numbers reuse the researched constants in the schedule generator.
- Multiple-choice evaluation is exact option-index match (selected index == `correct_index`).

### Nightly batch

- `generate_daily_lessons_task` iterates active schedules; for each whose weekday is in `days_of_week` it calls `get_or_create_daily_lesson` for tomorrow.

### Provenance and compare

- `lessons` gains a **`generator`** column (`rule | slm | both`) recording what produced the lesson.
- In `both` mode the orchestrator creates **two** Lesson rows for the same chapter + date, one per generator. `GET /lessons/daily` returns both with a switcher; completing one discards the other. Once the user has chosen, `LESSON_GENERATOR` is set to the winner and `both` mode stops producing the loser.

### Listening audio

- Listening items receive a TTS `audio_url` at generation time via the existing TTS service (online Edge, offline Piper fallback).

### Config

- New `LESSON_GENERATOR` setting, default `rule`; the small-LM path reuses the existing model file / path from curriculum escalation (CPU-only, ADR-0002).

## Testing Decisions

- **Seams** (confirmed): `lesson_service` is the primary seam; the new `ItemGenerator` protocol + dispatcher is the generator seam; `srs_service` is reused as-is. In-memory database per repo practice; coverage ≥80% gate (run `--no-cov` locally).
- `lesson_service` tests assert observable behavior: chapter lessons carry items with a `data` payload; answering a grammar item writes a card (correct → 4, incorrect → 1); flashcard self-rating drives SM-2; review slots fill up to 30% review-first in both chapter and generic lessons; `both` mode returns two lessons and completing one discards the other; an empty generation falls back to the generic lesson; old items (no `data`) still render.
- Generator tests: `RuleBasedGenerator` is tested directly for deterministic per-type extraction; `SlmGenerator` is tested via an injected fake adapter that returns known items (prior art: the fake-model tests in curriculum escalation); the dispatcher's selection per `LESSON_GENERATOR` is a one-line assertion.
- The nightly batch iteration is exercised at the `lesson_service` seam with mocked schedules (assert tomorrow's lesson is created for the right weekdays), not through Celery.
- Prior art: `test_lesson_service.py`, `test_curriculum_escalation.py`.

## Out of Scope

- A separate `cloze` item type (future; grammar MC-fill approximates it).
- FSRS scheduler (SM-2 for v1; `rate_card` is the drop-in seam).
- The schedule generator's 5th-day review / 10th-day quiz cadence overlay.
- Book categorization (genre × skill-focus) — a follow-on feature.
- GPU/iGPU SLM acceleration (CPU-only, ADR-0002).
- Changes to retrieval (`hybrid_search`) or chunking.

## Further Notes

- Research: `research/findings.md` (2026-08-14) — item-type feasibility, JLPT item shapes, SRS integration and pacing, the generator design.
- ADR-0003 (recall-only deck). The CPU-only SLM decision extends ADR-0002.
- Domain glossary: `CONTEXT.md` (Lesson item, Lesson generator, Curriculum map, Chapter, Known pages).
- Frontend: `/learning` renders the per-type structured items (options, passage, audio), review cards as flashcards, and the rule/SLM switcher in `both` mode; the item renderers and item types already exist.
