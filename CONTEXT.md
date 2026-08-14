# LinguaNotebook — Curriculum & Learning context

Turns uploaded PDFs into a searchable knowledge base and generates personalized daily lessons. The curriculum context owns how a document's structure (parts → chapters → pages) is detected and how daily lessons consume it chapter by chapter.

## Language

**Curriculum map**:
The extracted structure of a document — its parts, chapters (or units/lessons), and the page range each covers — used to drive daily lessons one chapter at a time.
_Avoid_: table of contents, outline (a map may be read from a TOC *or* from body headings)

**Chapter**:
A unit of learning within a document that a daily lesson draws on, identified by a structural marker (e.g. 章/課, 장/과, unit/lesson) and a start page.
_Avoid_: section (reserved for a deeper level than chapters)

**Part**:
An optional top-level grouping of chapters (e.g. 第1部). A book may have none.
_Avoid_: volume, book

**Structure source**:
Where a curriculum-map entry was read from — the document's table of contents (**TOC source**) or its body headings (**body-heading source**). The TOC source is preferred when it reads confidently; the body-heading source is the fallback.
_Avoid_: origin

**Structural-marker registry**:
The language-agnostic set of markers the extractor scans for, each tagged with a structural level (part/chapter/unit/lesson). Markers from many languages are merged into one registry — 部/章/課 are shared across CJK, so detection never depends on knowing the document's language.
_Avoid_: lexicon per language, gazetteer

**Content-association cross-check**:
Verifying that a candidate chapter title seen in the TOC also reappears in the document's body. Used as a *confidence measure*, never a hard filter — OCR-mangled titles must not drop valid chapters.
_Avoid_: verification pass (ambiguous with decoder verification)

**Confidence gate**:
The score (0–1) at which the rule-based extractor's result is trusted. High → trust the TOC scan; mid → prefer body headings; low → escalate to the optional small-LM fallback.
_Avoid_: confidence threshold

**Escalation**:
The action of calling the optional small-language-model fallback when the rule scan's confidence is below the gate. Runs in the parse worker, offline, only when a model file is present.
_Avoid_: fallback to LLM (ambiguous), LLM pass

**Known pages**:
The set of page numbers that actually exist in a document (read from its `--- Page N ---` markers). Any page number an extraction method reports must be a member of this set; a number outside it is treated as a hallucination.
_Avoid_: page whitelist (implementation-flavored), valid pages

**Lesson item**:
The smallest unit of study in a daily lesson — one of four types: flashcard, reading, grammar, or listening comprehension. Each carries a rendered question and correct answer plus a structured per-type payload (e.g. four answer options, a passage, a term and its reading) that the lesson generators produce.
_Avoid_: exercise (overloaded), question card

**Lesson generator**:
The component that builds lesson items from a single knowledge chunk. A deterministic rule-based generator is the always-on floor; an optional offline small-language-model generator (CPU-only, the same seam as curriculum escalation) produces richer items behind the same interface.
_Avoid_: lesson builder, item factory
