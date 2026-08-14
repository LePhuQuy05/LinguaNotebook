# Language Learning Methods — Research Synthesis for LinguaNotebook

**Date**: 2026-07-25
**Purpose**: Evidence-based foundation for LinguaNotebook's learning engine design
**Status**: Bootstrap complete

---

## Executive Summary

The research reveals that the most effective language learning approach is **multi-modal, input-rich, and adaptive** — not a single method but a strategic combination of techniques. Below is a ranked synthesis organized by evidence strength and practical applicability to LinguaNotebook's document-first, RAG-powered architecture.

---

## 1. Comprehensible Input (i+1) — THE FOUNDATION

**Evidence**: Stephen Krashen's Input Hypothesis — the most influential theory in SLA. Language is acquired through understanding messages slightly beyond current level (i+1). Supported by decades of empirical research.

**Core Mechanism**: Learners acquire language when focused on **meaning**, not form. Exposure to compelling, understandable content drives acquisition naturally.

**For LinguaNotebook**:
- Documents uploaded by users ARE comprehensible input when matched to their proficiency level
- The RAG system can filter/sort content by difficulty (i+1 matching)
- Auto-extract vocabulary and grammar patterns that appear naturally in user's own materials
- **Key insight**: Don't just parse documents — **rank and sequence content by comprehensibility** based on user's stated level

**Sub-techniques**:
- **Narrow Reading**: Multiple texts on the same topic → natural vocabulary repetition. LinguaNotebook can cluster documents by topic/domain.
- **Graded Progression**: Graded readers → light reading → popular literature → serious literature. LinguaNotebook can auto-classify documents into this progression.
- **Compelling Input**: Content so engaging the user forgets it's in another language. Let users upload what they LOVE.

---

## 2. Spaced Retrieval Practice — THE RETENTION ENGINE

**Evidence**: 2025 study in *Language Teaching Research* — combining retrieval practice + expanding-interval spaced repetition + feedback improved accuracy by **18 percentage points** (vs. 8% for cramming), with gains lasting at least 11 days.

**Core Mechanism**: Actively recalling information at strategically expanding intervals strengthens memory traces far more than passive re-reading.

**For LinguaNotebook**:
- Already planned (US5 — Spaced Repetition, SM-2 algorithm)
- **Enhancement**: Don't just schedule flashcards. Apply spaced retrieval to ALL content types:
  - Grammar patterns from parsed documents → recall exercises at expanding intervals
  - Sentence structures → fill-in-the-blank with feedback at spaced times
  - Pronunciation practice → re-listen and repeat at spaced intervals
- **Feedback is critical**: The research shows spacing + retrieval WITHOUT feedback is much less effective. Every review card MUST provide the correct answer immediately.

---

## 3. Extensive Reading — THE VOLUME PLAY

**Evidence**: 2025 meta-analysis in *Educational Psychology Review* — extensive reading positively impacts **all language domains**: reading, vocabulary, fluency, writing, speaking, AND motivation. Effects were larger with:
- Somewhat limited text choice (level-matched, not completely free)
- Accountability included (brief quizzes, reports)

**Core Mechanism**: Large-volume, pleasurable reading provides massive comprehensible input with natural vocabulary repetition in context.

**For LinguaNotebook**:
- This is LinguaNotebook's **killer feature** — users already HAVE their reading materials (PDFs)
- Auto-generate **comprehension quizzes** from parsed documents (accountability = better results)
- Track reading volume (pages read, words encountered) and display in dashboard
- **Reading streak tracking** alongside study streak — gamify reading volume
- Suggest "what to read next" from user's library based on difficulty progression

---

## 4. Oral Narrative / Storytelling — THE ENGAGEMENT MULTIPLIER

**Evidence**: 2025 meta-analysis in *System* — storytelling interventions produced **medium-to-large effects** on speaking, reading, grammar, and vocabulary. Most effective for intermediate learners with medium-term interventions.

**Core Mechanism**: Narratives provide contextually rich, emotionally engaging input that makes vocabulary and grammar memorable. Stories activate multiple brain regions simultaneously.

**For LinguaNotebook**:
- Auto-extract narrative passages from user's documents
- Generate **story-based listening exercises**: TTS reads a story segment → comprehension questions
- **Digital storytelling**: Let users create their own stories using vocabulary from their documents
- For fiction/literature PDFs, preserve narrative structure in parsed output

---

## 5. AI-Guided Personalized Learning — THE DIFFERENTIATOR

**Evidence**: 2024 meta-analysis in *Language Learning & Technology* (61 studies, N=8,282) — AI-guided individualized learning had **large within-group effect (d=1.18)**. Machine learning + hybrid approaches outperformed rule-based systems.

**Core Mechanism**: Adaptive systems that personalize content difficulty, pacing, and review schedules based on individual performance outperform one-size-fits-all approaches.

**For LinguaNotebook**:
- RAG system already enables personalization (user's own documents)
- **SRS data** (ease factor, response time, accuracy per content type) can drive adaptive difficulty
- Auto-adjust daily lesson composition based on performance trends
- **Predictive modeling**: Identify which content types/patterns the user struggles with → increase those in future lessons

---

## 6. Multimodal Input (Dual Coding) — AMPLIFY EVERYTHING

**Evidence**: Cognitive science — combining verbal + visual information creates two memory traces, dramatically improving recall. In language learning: text + audio, text + images, text + context.

**Core Mechanism**: The brain processes verbal and visual information through different channels. Dual-coded memories are stronger and more resistant to forgetting.

**For LinguaNotebook**:
- Every flashcard: word + definition + **example sentence from source document** + **TTS audio** + **context image from PDF page**
- Reading passages: show the **original PDF page image** alongside parsed text
- Grammar exercises: extract the sentence **with surrounding context** so user sees grammar in situ
- Listening exercises: **text + audio simultaneously** (dual coding for listening comprehension)

---

## 7. Shadowing — THE PRONUNCIATION + FLUENCY HACK

**Evidence**: Developed by linguist Prof. Alexander Arguelles. Integrates visual, auditory, and kinesthetic learning simultaneously. Widely used by polyglots and military language programs.

**Core Mechanism**: Speaking aloud **simultaneously** with a recording (not repeating after) forces the brain to process input and produce output at native speed, building fluency and prosody.

**For LinguaNotebook**:
- **Shadowing mode**: Display parsed text → TTS plays → user speaks along simultaneously → microphone captures → compare waveforms/prosody
- **Scriptorium mode**: Display sentence → user reads aloud → user writes while reading aloud → user reads aloud again. LinguaNotebook can time and track this.
- **Side-by-side reading**: Show original + translation side-by-side from bilingual documents
- This is a **premium feature** — requires microphone, real-time audio processing

---

## 8. Interleaving — BEAT THE PLATEAU

**Evidence**: Cognitive science — mixing different topics/skills during study (vs. blocked practice) improves ability to discriminate between concepts and apply the right skill in the right context.

**Core Mechanism**: Blocked practice (AAAA BBBB CCCC) feels easier but produces worse long-term retention. Interleaving (ABC ABC ABC) feels harder but builds more robust, flexible knowledge.

**For LinguaNotebook**:
- Daily lessons should **interleave content types**: flashcard → reading → grammar → listening → flashcard → reading...
- Don't group all vocabulary first, then all grammar, then all reading — **mix them**
- The SRS engine should interleave review cards from different documents, topics, and time periods
- This is a simple but powerful design principle for lesson generation

---

## 9. Learning Through Media (Music, TV, Podcasts) — THE FUNNEL

**Evidence**: Multiple 2025 studies — songs + films produced **large to very large effect sizes (d=1.12–1.65)** for listening comprehension. 80% of students regularly use songs for language learning. Narrow viewing (watching successive episodes of same series) reduces lexical load and accelerates incidental vocabulary acquisition.

**Core Mechanism**: Entertainment media provides authentic, motivating, context-rich input. The enjoyment factor dramatically increases total exposure time (hours of voluntary practice).

**For LinguaNotebook**:
- While LinguaNotebook is document-first, the principles apply:
  - **Narrow reading/viewing**: Suggest reading multiple documents on the same topic or by the same author
  - **Audio-first mode**: Let users LISTEN to their parsed documents (TTS) while commuting — like a personalized podcast from their own books
  - **Transcript + audio sync**: Parse a transcript PDF, generate TTS, create synchronized reading+listening experience
  - Future: support uploading audio/video files with transcripts for dual-mode learning

---

## 10. Output Hypothesis — PRODUCE TO NOTICE GAPS

**Evidence**: Merrill Swain's Output Hypothesis — comprehensible input alone is insufficient. Learners need to **produce** language (speaking, writing) to notice gaps between what they want to say and what they can say.

**Core Mechanism**: When learners attempt to produce language, they become aware of what they DON'T know, which primes them to notice those forms in future input.

**For LinguaNotebook**:
- Add **production exercises** to daily lessons:
  - "Write a sentence using this word" (typed response)
  - "Summarize this paragraph in the target language"
  - "Answer this question in a complete sentence" (microphone or text)
- Auto-evaluate using LLM (RAG-powered): compare user response to expected patterns from source documents
- Track "noticing gaps" — patterns the user consistently gets wrong → increase exposure to those patterns

---

## Summary: The Optimal LinguaNotebook Learning Engine

| Rank | Method | Integration Priority | Evidence Strength |
|------|--------|---------------------|-------------------|
| 1 | Comprehensible Input (i+1) | Core architecture — difficulty-ranked content | Very High (decades) |
| 2 | Spaced Retrieval Practice | Already planned (SRS) — extend to all content types | Very High (2025 meta) |
| 3 | Extensive Reading | Document-first = built in. Add quizzes + tracking | Very High (2025 meta) |
| 4 | AI-Guided Personalization | SRS data → adaptive difficulty + content selection | High (2024 meta, d=1.18) |
| 5 | Multimodal/Dual Coding | Every learning item: text + audio + image + context | High (cognitive science) |
| 6 | Storytelling/Narrative | Extract narratives + story-based exercises | High (2025 meta) |
| 7 | Interleaving | Lesson generator: mix content types in each session | High (cognitive science) |
| 8 | Shadowing/Scriptorium | Premium feature — TTS + microphone + waveform | Medium (expert consensus) |
| 9 | Media/Entertainment Input | Audio-first mode, narrow reading, future: video/audio | High (2025 studies) |
| 10 | Output/Production | Writing + speaking exercises with LLM feedback | Medium-High (SLA theory) |

### Design Principles for Lesson Generation

1. **START WITH INPUT**: Every lesson begins with comprehensible input from the user's own documents (reading passage, audio segment, or both)
2. **RETRIEVE, DON'T RE-READ**: After input, immediately test recall (flashcards, questions) — no passive review
3. **INTERLEAVE**: Mix vocabulary, grammar, reading comprehension, and listening within each session
4. **DUAL-CODE EVERY ITEM**: Text + audio + visual context from source document
5. **SPACE + FEEDBACK**: Every review uses expanding intervals WITH immediate correct-answer feedback
6. **TRACK + ADAPT**: SRS performance data drives content difficulty, item selection, and review scheduling
7. **MAKE IT COMPELLING**: Content comes from the user's own chosen documents — intrinsically motivating

---

## 2026-08-14 — RAG-to-lesson generation & book skill categorization

**Scope.** The embed/index phase is done: parse → `_save_curriculum_structure` → `_dispatch_embed` → `embed_worker` → Qdrant hybrid index, and `generate_lesson` already walks the curriculum map. This section answers the two questions for the build phase: (Q1) what a real daily lesson is composed of when its raw material is textbook chunks in Qdrant, and (Q2) how to categorize each book by skill focus and drive lessons from that. Both answers are grounded in the seams that exist in `backend/src/` and in how mature systems (Anki/FSRS, WaniKani, Bunpro, Satori Reader, LingQ) and the JLPT/CEFR structure handle the same problem.

### Executive answer — Q1: turning embedded chapters into a real daily lesson

**Composition.** A daily lesson is a **chapter-anchored interleaving of five item families** built from the current curriculum chapter's chunks (not random global retrieval). For a 10-item lesson (the `Schedule.daily_item_count` default, ~15–30 min) the spine is:

| Slot | Item | Code seam that implements it | Notes |
|---|---|---|---|
| 1 | **Comprehensible-input passage** — one chapter chunk, read + TTS audio (dual-coding) | `lesson_service._next_chapter` + `hybrid_search(..., document_id, page_start, page_end)` inside `_generate_chapter_lesson`; audio via `tts_service.synthesize` | "START WITH INPUT" (this synthesis, §Design Principles). Present as `ItemType.reading`. |
| 2–4 | **Vocabulary cards** — word → reading → source sentence + audio | candidates from `structure_extractor.extract_vocabulary_from_content` (kanji+furigana regex) or word\|reading\|meaning table chunks; stored as `ItemType.flashcard` | Card = {word, reading, source sentence}, **not** the whole chunk as the answer (gap 2 below). |
| 5–6 | **Cloze (typed fill-in-the-blank)** on a chapter sentence | needs a new `ItemType.cloze` + frontend component; heuristic masking is fully offline | Bunpro's model — active recall with an accepted-alternatives list ([S4]). |
| 7 | **Grammar-pattern spot** — "which chapter sentence uses 〜ば/〜のに/…?" | needs a small per-language pattern registry fed from grammar chapters | JLPT "text grammar" item type ([S2]). |
| 8–9 | **Due SRS reviews** interleaved | `srs_service.get_due_cards` — already wired in `_generate_generic_lesson`, **missing from the chapter path** | The retention engine; reserve ~20–30% of slots. |
| 10 | **Production prompt** — "write a sentence using this word" | `ItemType.flashcard` with `self_rating`, or a new `ItemType.production` | Output Hypothesis (Swain); self-graded offline, LLM-graded when available. |

**Retrieval/selection strategy — three sources, in priority order.**
1. **Curriculum progress first** (i+1 by construction). `_next_chapter` already returns the most-advanced book's lowest-order unfinished chapter; `_generate_chapter_lesson` already scopes retrieval to `document_id` + `page_start`/`page_end` and sorts chunks by `(page_start, chunk_index)` into book order. Keep this — it is the correct i+1 spine for a graded textbook (chapters sequence the learner through the book's own difficulty curve).
2. **SRS-due reviews second** (spaced retrieval). The chapter path does not mix in `get_due_cards`; the generic path does. Add a fixed review fraction to `_generate_chapter_lesson` (`max(1, round(total_items * 0.25))` slots), linked via `SRSCard.knowledge_segment_id` → the same Qdrant point id a `LessonItem` carries. The 2025 retrieval-practice study ([S7]) shows spacing + retrieval + immediate feedback is the retention engine — and it generalizes to sentence/grammar recall, not just word cards.
3. **i+1 difficulty matching third** (adaptive, optional). `hybrid_search` already accepts a `difficulty` filter, but `embed_service.embed_and_index_chunks` hard-codes `"difficulty": "intermediate"` on every payload and `ContentBlock.difficulty_level` defaults to `"intermediate"` — the filter is currently dead. Populate it at embed time with offline proxies: (a) **known-word coverage** — a token is "known" if it appears as the `front` of an `SRSCard` that passed a milestone (`repetitions >= 2`); target passages at ~85–98% coverage ([S10]); (b) **structural difficulty** — sentence length and kanji density from `payload.token_count`/`content`; (c) **book-declared level** — inherit from the category/label (an N3 語彙 book's chapters are N3), never guess per-chunk in a vacuum. Cold-start fallback: the user's stated JLPT level (`schedule_generator.Difficulty`, N5→N1) seeds the known-word base with frequency-band assumptions. Mandarin Mosaic is the pure form — every word known except exactly one new per sentence ([S11]); LingQ's known-word model ([S6]) is the softer variant.

**Item-type feasibility (offline vs optional local LLM).**

| Item type | Offline (rule-based) | Optional local LLM tier | Where it plugs in |
|---|---|---|---|
| Vocabulary card | ✅ regex/table extraction + `tts_service` | — | `_create_lesson_item` / `ItemType.flashcard` |
| Cloze (typed) | ✅ heuristic mask of a chapter target word + accepted-alternatives list | LLM picks the pedagogically best word / distractors | new `ItemType.cloze` + `frontend/src/components/learning/*` component |
| Grammar-pattern spotting | ✅ per-language pattern registry | LLM extracts patterns from grammar chapters | `ItemType.grammar` enrichment |
| Reading comprehension Q&A | ⚠️ templates only (main idea / true-false) | ✅ LLM generates questions + plausible distractors grounded in the chunk (RAG-QG, e.g. ClimaGen [S9]) | `ItemType.reading` |
| Listening (TTS) | ✅ `tts_service.synthesize` + keyword-overlap grading in `answer_item` | — | existing `ItemType.listening` |
| Production/writing | ✅ self-graded (`self_rating`); exact-string for constrained prompts | ✅ LLM feedback on free text | `ItemType.flashcard` or new `ItemType.production` |

The spec (FR-009) already sanctions a small local model for item generation. The repo's sanctioned offline-LLM seam is `curriculum_escalation.py` — lazy `llama-cpp-python`, CPU-only, process-cached, whitelist-verified output. Reuse that exact pattern (same `Qwen3-4B Q4_K_M` file, or `Qwen3-1.7B` for CPU speed) as an **escalation/optional** tier for MCQ generation and free-answer evaluation, with the rule-based items as the always-on floor. This preserves the offline-first contract (FR-021/022). Note on listening: `tts_service` uses Edge TTS (online) with Piper (offline) as fallback — for true offline-first, either pre-warm the Redis TTS cache or fall back to Piper.

**SRS + scheduling integration — reuse the seams, don't rebuild.**
- **Write-back is the missing link.** `complete_lesson` computes a score but never creates `SRSCard`s; `_generate_generic_lesson` only *reads* due cards. Wire: on `answer_item`/`complete_lesson`, call `srs_service.create_card(db, user_id, front, back, segment_id=item.knowledge_segment_id)` — the card and the lesson item already share the Qdrant point id, and `get_due_cards`/`rate_card` (SM-2) already implement the schedule.
- **The beat task is a stub.** `lesson_worker.generate_daily_lessons_task` returns `{"lessons_generated": 0}`. Implement it: iterate active schedules (`schedule_service.get_schedules`), and on `weekday in schedule.days_of_week` call `lesson_service.get_or_create_daily_lesson` for tomorrow.
- **Pacing.** `schedule_generator` already encodes the researched pacing — `NEW_ITEMS_PER_SESSION` (15/12/10/8/5 for N5→N1) and `SM2_INTERVALS` (1,3,7,14,30,60,120,240). Use its per-level numbers to set `Schedule.daily_item_count` and the new-vs-review split; keep the 5th-day-review / 10th-day-quiz cadence as an optional overlay.
- **Algorithm upgrade path.** SM-2 is fine for v1, but FSRS ([S1]) reaches the same retention with fewer reviews, adapts per user, and handles overdue reviews far better. `rate_card` is one function — swapping in an FSRS scheduler is a drop-in change behind the same seam; desired-retention is the only knob users need.

**Gaps to close in code (build order).** (1) Real item construction in `_create_lesson_item` — stop using the whole chunk as the flashcard answer; (2) SRS write-back in `complete_lesson`; (3) due-review slots in `_generate_chapter_lesson`; (4) attach a TTS audio URL to `ItemType.listening` items; (5) new `ItemType.cloze` + frontend component; (6) implement the `lesson_worker` beat task; (7) category + difficulty awareness (Q2).

### Executive answer — Q2: book skill-category taxonomy & offline classification

**Taxonomy — two orthogonal axes, not one flat enum.** A single flat category fights the data: an N3 CHOUKAI (聴解) book is simultaneously a *workbook* (numbered sections, answer key) and *listening* (skill focus). Recommend two tags on `Document` (new columns; FR-035 already promises user-editable categorization):

- **`book_genre`** — how the book is organized: `textbook` (integrated course — dialogue+grammar+vocab+reading+audio; Genki/Minna style), `workbook` (companion drills, numbered sections, answer key), `reader` (graded/extensive reading, level-controlled stories), `exam-prep` (mock tests, 模擬/実力), `reference` (grammar reference / dictionary / appendix), `kanji-workbook` (dedicated 漢字/字 book).
- **`skill_focus`** — what the book trains, mirroring JLPT sections + CEFR skills ([S2], [S8]): `vocabulary`, `grammar`, `kanji` (kanji·hanzi), `listening`, `reading`, `writing`, `mixed` (textbook default). JLPT's own structure — Language Knowledge (Vocabulary), Language Knowledge (Grammar)・Reading, Listening ([S2]) — is the natural source for these labels.

For an MVP a single flat enum works: `textbook`, `workbook`, `vocabulary`, `grammar`, `kanji`, `listening`, `reader`, `exam-prep`, `reference` (a listening workbook records `listening`; genre absorbed into skill). Two axes is recommended because genre and skill modulate the generator independently.

**Offline classification signals** (all already present in the pipeline — reuse, no cloud):

| Signal | Evidence in parsed markdown / map | Reliability | Where it already exists |
|---|---|---|---|
| Structural markers (課/章/単元/Unit/Chapter/Lesson) | TOC scan finds marker-based chapters → textbook-ish | High | `curriculum_service._MARKERS` / `_extract_entries` |
| Numbered sections with no marker (`## 2 ポイント理解`) | → workbook (listening/grammar workbooks) | High | `curriculum_service._extract_numbered_sections` |
| Answer-key rows (`## 1 番 答え4`) | → exam-prep or workbook | High | `curriculum_service._ANSWER_KEY_RE` |
| Practice/test section titles (まとめ/復習/テスト/模擬/実力/연습/答案/練習/Appendix/Index/…) | → exam-prep; or textbook chapter-end review | High | `curriculum_service._STOPLIST_BY_LANGUAGE` |
| Block-type distribution (header/table/list/paragraph counts) | vocab books are table-heavy (word\|reading\|meaning); grammar books paragraph-heavy | Medium | `ContentBlock.block_type` (already preserved through chunking) |
| Skill cue words | 語彙/単語/ことば/意味 → vocabulary; 文法/表現 → grammar; 漢字/読み/書き/部首 → kanji; 聞き取り/リスニング/聞く/CD → listening; 読解/読み物 → reading; 作文/書く → writing | Medium | new — a per-language cue lexicon shaped like `_STOPLIST_BY_LANGUAGE` |
| Exercise density (問/番/問題, list+table ratio) | high → workbook/exam-prep | Medium | compute over `ContentBlock`s |
| Page/chunk count | long+dense → reference/exam-prep; short → reader | Low | `Document.total_pages` / `chunks_count` |

**Classifier design — rules first, LLM escalation only on low confidence.** Build `backend/src/services/book_classifier.py` mirroring `curriculum_service`'s philosophy (conservative, rule-based, unit-testable, ≥80% coverage): a weighted score over the signals above → `{genre, skill_focus, confidence}`. Run it in `parse_worker` right after `_save_curriculum_structure` (which already runs there) and persist on `Document`. When the rule score is below a gate, escalate with the **same** optional local-LLM seam as `build_curriculum_escalator` — a light `llama-cpp-python` call over a few signal pages, constrained to the category enum, verified deterministically. Classification is simpler than TOC recovery, so rules cover the common cases; the LLM is a safety net, never the default — the same conclusion the curriculum research already reached (`docs/research/curriculum-extraction-generalization.md` §2.4).

**What each category drives in the lesson generator (keys into Q1).**

| Category | Default `content_types` mix (overrides `CONTENT_RATIOS`) | Dominant item types | Lesson behavior |
|---|---|---|---|
| `textbook` | current `CONTENT_RATIOS` (vocab .40 / reading .25 / grammar .20 / listening .15) | balanced, chapter-anchored | default interleaved lesson; chapter-end まとめ sections become review slots |
| `workbook` | grammar + listening heavy | cloze, grammar drills, quiz | exercise-dense, fewer "new material" items; answer-key pages never become lessons |
| `vocabulary` | vocabulary .8 / reading .2 | flashcards, cloze | SRS-first; high `NEW_ITEMS_PER_SESSION`; cards from word\|reading\|meaning tables |
| `grammar` | grammar .6 / reading .2 / vocab .2 | pattern-spotting, cloze on example sentences | patterns registered from the book; JLPT "sentential grammar" drill shapes |
| `kanji` | vocabulary (kanji cards) + reading | kanji card (meaning+reading+mnemonic); radical→kanji→vocab unlock chain | WaniKani-style level gating: kanji unlocks vocab that uses it ([S3]) |
| `listening` | listening .6 / reading .4 | TTS-first, shadowing, key-point comprehension (JLPT listening item types, [S2]) | audio-first; transcripts dual-coded as text+audio |
| `reader` | reading .7 / vocabulary .3 | comprehension Q&A (LLM tier), shadowing, narrow reading | i+1 sequencing is the whole point; comprehension accountability (extensive-reading meta, §3 above) |
| `exam-prep` | mixed quiz | timed mock sections mapped to JLPT item types | answer-key pages become instant-check quizzes |
| `reference` | none | study/search mode | not lesson-driven; surfaced for lookup |

**Implementation seams.** Add `CATEGORY_CONTENT_RATIOS: dict[str, dict[str, float]]` next to `CONTENT_RATIOS` in `lesson_service`; make `_validate_schedule` (`schedule_service`) accept category-derived `content_types`; extend `_create_lesson_item` to build cloze/kanji/production items by category; make `_chapter_query` category-aware (`<topic>の文法` for grammar chapters, plain `<topic>` for listening/vocab, so BGE-M3 matches better).

### Sources

1. FSRS: [open-spaced-repetition/fsrs4anki — The Algorithm](https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-Algorithm) · [Expertium, "A technical explanation of FSRS"](https://expertium.github.io/Algorithm.html) · [Anki FAQs — spaced-repetition algorithm](https://faqs.ankiweb.net/what-spaced-repetition-algorithm)
2. [JLPT official — Composition of Test Sections and Items (Vocabulary / Grammar・Reading / Listening by level)](https://www.jlpt.jp/e/guideline/testsections.html)
3. [WaniKani Knowledge — Unlocking Kanji (radicals→kanji→vocab, SRS stages)](https://knowledge.wanikani.com/getting-started/unlocking-kanji/)
4. [Bunpro Community — how BunPro chooses the next example sentence (cloze SRS, alternate answers)](https://community.bunpro.jp/t/how-does-bunpro-decide-you-re-ready-for-the-next-example-sentence/163594) · [Tofugu review of Bunpro](https://www.tofugu.com/reviews/bunpro/)
5. [Satori Reader (App Store) — tap-to-translate, sentence TTS, SRS cards built from reading](https://apps.apple.com/us/app/satori-reader/id1382950847)
6. [LingQ Blog — Best Books to Learn Japanese (textbook / workbook / grammar reference / kanji book / graded reader genres)](https://www.lingq.com/blog/blog-best-books-to-learn-japanese/)
7. Karatas, Özemir, Lovelett, et al., "Improving Second Language Vocabulary Learning and Retention by Leveraging Memory Enhancement Techniques," *Language Teaching Research* 29(1):112–149, 2025 — [DOI 10.1177/13621688211053525](https://doi.org/10.1177/13621688211053525) · [ERIC EJ1455908](https://eric.ed.gov/?id=EJ1455908)
8. [Council of Europe — CEFR level descriptions (can-do skill descriptors for reading/listening/speaking/writing)](https://www.coe.int/en/web/common-european-framework-reference-languages/level-descriptions)
9. [ClimaGen — RAG + prompt engineering for automatic cloze/QA generation from textbooks, arXiv:2410.16701](https://arxiv.org/abs/2410.16701)
10. [i+1 comprehensible-input coverage thresholds (~95–98% known words) — synthesis used here](https://lingoseven.com/vi/blog/comprehensible-input-explained/) (citing Hu & Nation 2000; Laufer & Ravenhorst-Kalovski 2010; van Zeeland & Schmitt 2013)
11. [Mandarin Mosaic — "every word known except exactly one new" sentence-level i+1 selection](https://apps.apple.com/jp/app/mandarin-mosaic-learn-chinese/id1625096539)
