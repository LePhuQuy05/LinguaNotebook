# 03 — SRS write-back + due-review slots

**What to build:** Answering a recall-able item writes or updates that item's SRS card immediately — flashcards from their self-rating, grammar multiple-choice from correctness (correct→4, wrong→1). Every lesson (chapter and generic) reserves up to 30% of its items for the user's due cards, surfaced review-first as flashcard items; each review item carries its card reference so answering it rates the card on the spaced schedule. Reading and listening items never create cards (recall-only deck). Deck-free users get full new-item lessons.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Answering a grammar item creates/updates a card with the correct SM-2 state for the outcome
- [ ] Answering a flashcard drives the card from the self-rating
- [ ] Due cards fill up to 30% of a chapter lesson's items, review-first, as flashcard items carrying the card reference
- [ ] Rating a review item updates the card's interval/repetitions
- [ ] Reading and listening items never create cards
- [ ] With no due cards the lesson is all new items; coverage ≥80% at the lesson-service seam
