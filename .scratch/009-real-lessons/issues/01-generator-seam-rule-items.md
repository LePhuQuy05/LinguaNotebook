# 01 — Generator seam + rule generator + structured items

**What to build:** A lesson's items stop being whole-chunk dumps and become real, structured items produced by a deterministic rule-based generator behind a swappable seam. The item table gains a JSON `data` column holding the per-type payload: flashcards carry term/reading/definition/example; reading, grammar-fill, and listening items carry a passage/prompt/text plus four answer options and the correct index. `question` and `correct_answer` remain the rendered strings so old items (no `data`) keep working. Multiple-choice answers are graded by exact option-index match; flashcards stay self-rated. The daily lesson response exposes each item's `data`.

Gotcha: the running dev database needs the new column added by hand — the schema tool does not alter existing tables.

**Blocked by:** None — can start immediately.

**Status:** completed

- [x] A chapter lesson's items carry a per-type `data` payload produced by the rule generator
- [x] Flashcard items show term, reading, definition, example; MC items expose four options + correct index
- [x] Selecting the correct option grades the item correct; any other option wrong; flashcard uses self-rating
- [x] The daily lesson response includes each item's `data` and options
- [x] Old items without `data` still render and answer as today
- [x] The generator seam is one protocol with a dispatcher driven by the generator setting; `rule` is the default
- [x] Coverage ≥80% at the lesson-service and generator seams
