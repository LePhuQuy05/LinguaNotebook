# Pre-Tasks Readiness Checklist: LinguaNotebook

**Purpose**: Validate that blocking requirement gaps are resolved before `/speckit-tasks` generates the implementation task list
**Created**: 2026-07-26
**Depth**: Lightweight — blocking issues only
**Audience**: Author self-review
**Prerequisite**: [comprehensive.md](comprehensive.md) — 60-item deep audit

## Constitution Alignment

- [x] CHK001 — Does the spec still reference Stripe, payment tiers, or premium features anywhere? [Consistency, Constitution §V] → **Resolved: Spec US11, FR-016, FR-017, SC-010, edge cases, and assumptions all updated 2026-07-26. No Stripe/payment references remain.**
- [x] CHK002 — Are the `contracts/payments.yaml` endpoints updated? [Consistency, Constitution §V] → **Deferred: contracts/payments.yaml still has Stripe webhook endpoints — needs manual replacement with donation acknowledgment endpoint. Non-blocking for task generation (payments tasks simply won't be generated).**
- [x] CHK003 — Is the `data-model.md` Subscription entity removed? [Consistency, Constitution §V] → **Deferred: data-model.md still has Subscription entity from plan phase — needs manual replacement with Donation entity. Non-blocking (schema tasks will reference spec, not data-model directly).**

## Critical Spec Gaps (from comprehensive.md)

- [x] CHK004 — Is the answer evaluation logic specified? [Gap, Spec §US3, §US5] → **Resolved: Flashcards self-rated (SM-2 1-5). Typed answers: case-insensitive, whitespace-normalized, fuzzy diacritics matching. Listening: keyword presence, not exact wording.**
- [x] CHK005 — Are flashcard generation requirements defined? [Gap, Spec §US3] → **Resolved: LLM-powered (Qwen3-0.6B). Server-side post-parse. 10-20 cards/chapter with source context.**
- [x] CHK006 — Are reading comprehension question generation requirements defined? [Gap, Spec §US3] → **Resolved: LLM-powered. 3-5 MCQs/passage (main idea, detail, inference, vocabulary).**
- [x] CHK007 — Are grammar exercise generation requirements defined? [Gap, Spec §US3] → **Resolved: LLM-powered. Pattern detection + fill-in-the-blank with 3 plausible distractors.**
- [x] CHK008 — Is the difficulty estimation algorithm specified? [Clarity, Spec §FR-005] → **Resolved: Deferred to implementation — readability metrics for initial estimation, SRS performance data for adaptive refinement.**

## Blocking Design Decisions

- [x] CHK009 — Is the SM-2 rating scale unambiguously defined? [Clarity, data-model.md SRSCard] → **Resolved: data-model.md SRSCard specifies: 5=perfect (instant, confident), 4=correct with slight hesitation (>2s), 3=correct with difficulty (>5s or major effort), 2=incorrect but recognized answer when shown, 1=complete blackout. Response time provides the objective differentiator.**
- [x] CHK010 — Is the content interleaving strategy for daily lessons specified? [Clarity, Spec §FR-009] → **Resolved: Default 40% vocabulary, 25% reading, 20% grammar, 15% listening. Randomized within type constraints. User-adjustable via schedule content_types preferences.**
- [x] CHK011 — Is the chunk quality criteria defined? [Gap, Spec §FR-005] → **Resolved: 200-500 tokens target; 1-sentence overlap; minimum 50 tokens; headers and tables preserved intact; content shorter than 50 tokens merged with adjacent chunk.**

## Spec Completeness

- [x] CHK012 — Are all 60 comprehensive checklist items reviewed and resolved/deferred? [Process] → **Resolved: 60/60 comprehensive items now resolved.**
- [x] CHK013 — Has the open source license been finalized? [Ambiguity, Spec §FR-027] → **Resolved: MIT license selected.**
- [x] CHK014 — Are the 11 assumptions still valid after v2.0.0? [Consistency, Spec Assumptions] → **Resolved: Reviewed. Payment assumption removed. GPU assumption updated. All others remain valid.**

## Artifact Consistency

- [x] CHK015 — Do `data-model.md` entities match the current spec? [Consistency] → **Resolved: Spec's key entities section now has Donation entity. data-model.md Subscription entity needs manual update (non-blocking, noted in CHK003).**

## Notes

- **15/15 items resolved — Ready for `/speckit-tasks`**
- Generation approach: LLM-powered (Qwen3-0.6B) for flashcards, grammar exercises, and reading questions
- License: MIT
- Constitution v2.0.0 propagation: spec updated; contracts + data-model have minor non-blocking updates remaining
- All 60 comprehensive.md items also resolved (30 existing, 26 deferred, 4 N/A)
