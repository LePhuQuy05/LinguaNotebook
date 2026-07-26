# 🦉 LinguaNotebook — Spec-Kit Prompts (English)

> **Goal**: Build a production-grade, monetizable language learning web app with HPD-Parsing based document ingestion, advanced RAG, customizable study schedules, daily AI-powered lessons, and multilingual TTS voice system.

---

## 🔢 Spec-Kit Execution Order

Run the following slash commands in this exact order:

```
1. /speckit-constitution  →  Establish project principles & governance
2. /speckit-specify       →  Create feature specification (spec.md)
3. /speckit-clarify       →  Resolve ambiguous areas (optional, before plan)
4. /speckit-plan          →  Create implementation plan (plan.md + research.md + data-model.md + contracts/)
5. /speckit-checklist     →  Generate quality checklist (optional)
6. /speckit-analyze       →  Cross-artifact consistency check (optional, before implement)
7. /speckit-tasks         →  Generate actionable, dependency-ordered tasks (tasks.md)
8. /speckit-implement     →  Execute implementation from tasks.md
9. /speckit-converge      →  Assess codebase & append remaining work as tasks
```

---

## 1️⃣ CONSTITUTION PROMPT

Command: `/speckit-constitution`

```
Establish the project constitution for LinguaNotebook — a production-grade,
monetizable web application for deep language learning powered by personal documents.

CORE PRINCIPLES:

I. Document-First Learning (NON-NEGOTIABLE)
- All learning content MUST originate from user-uploaded documents (PDFs, images)
- HPD-Parsing (PaddlePaddle, 1B params) MUST parse every document into structured markdown:
  headers, tables, text blocks, with bounding boxes
- Parsed output MUST be normalized and stored in a vector database for RAG retrieval
- ABSOLUTELY NO hardcoded or canned learning content — everything comes from user documents

II. RAG-First Architecture (NON-NEGOTIABLE)
- RAG (Retrieval-Augmented Generation) MUST be the central pathway for all knowledge queries
- Vector database (Qdrant) MUST store embeddings from all parsed content
- Hybrid search is MANDATORY: dense vector + sparse keyword (BM25) + metadata filtering
- RAG pipeline MUST support incremental index updates when users upload new PDFs
- No knowledge MUST ever be returned to the user without going through the RAG pipeline

III. Voice-First Interface
- Every piece of learning content MUST be listenable via Text-to-Speech (TTS)
- Multi-language support REQUIRED: English, Vietnamese, Chinese, Japanese, Korean, French,
  German, Spanish (minimum 8 languages)
- Edge TTS as primary (online, free, high quality) + Piper TTS as fallback (offline mode)
- Waveform visualization MUST render during audio playback
- Users MUST be able to select voice gender, speed, and language per content item

IV. Adaptive Learning Schedule
- Users MUST be able to create fully customizable study schedules: time, frequency, goals,
  content type preferences
- System MUST auto-generate daily lessons from RAG content matched to the user's schedule
- Spaced Repetition System (SRS, SM-2 algorithm) MUST be integrated for optimal retention
- Dashboard MUST track: daily streaks, vocabulary learned, total study time, progress charts

V. Production-Ready & Monetizable
- Microservices architecture: parsing service, RAG service, schedule service, API gateway
- Authentication & authorization: JWT + OAuth2 (Google, GitHub)
- Payment integration: Stripe for subscription billing (Free / Pro $9.99/mo / Team $29.99/mo)
- Rate limiting, structured logging, monitoring: Prometheus + Grafana, Sentry for errors
- Docker + Docker Compose for development; Kubernetes-ready for production
- CI/CD pipeline via GitHub Actions (test → build → deploy)

VI. Code Quality & Testing (NON-NEGOTIABLE)
- Test-First Development: write tests BEFORE implementation
- Unit tests (pytest), integration tests, contract tests, E2E tests (Playwright)
- Type hints mandatory for all Python code (mypy strict mode)
- Minimum 80% code coverage enforced
- Every API endpoint MUST have OpenAPI/Swagger documentation
- Linting & formatting: ruff, black, prettier, eslint

VII. Security & Privacy
- All uploaded files MUST be virus-scanned before processing
- Document content MUST be encrypted at rest (AES-256)
- Strict user data isolation: each user sees ONLY their own data
- GDPR-compliant data handling with data export and deletion endpoints
- Input sanitization on every endpoint; CSP headers; SQL injection prevention via ORM

TECHNICAL CONSTRAINTS:
- Backend: Python 3.11+, FastAPI, Celery (background tasks), SQLAlchemy (ORM)
- Frontend: TypeScript, React 18+, Next.js 14 (App Router), Tailwind CSS, shadcn/ui
- Relational DB: PostgreSQL 15 (users, schedules, progress, subscriptions)
- Vector DB: Qdrant (embeddings, hybrid search)
- Cache: Redis (sessions, rate limiting, Celery broker, TTS audio cache)
- ML/MLOps: HPD-Parsing (PaddlePaddle), BGE-M3 (embeddings), Piper TTS, Edge TTS
- Infrastructure: Docker Compose (dev), GitHub Actions (CI/CD)
- Deploy targets: Vercel (frontend), Railway or AWS ECS (backend services)
- GPU requirement: minimum 8GB VRAM for HPD-Parsing (NVIDIA CUDA or Intel Arc XPU)

GOVERNANCE:
- This constitution is the supreme document of the project; all PRs MUST verify compliance
- Amendments require: documentation, stakeholder approval, migration plan
- Any added complexity MUST be explicitly justified in plan.md Complexity Tracking table
- Version: 1.0.0 | Ratified: 2026-07-25 | Last Amended: 2026-07-25
```

---

## 2️⃣ SPECIFY PROMPT

Command: `/speckit-specify`

```
Build LinguaNotebook — a web application for deep language learning powered
by personal documents, advanced RAG, customizable schedules, daily AI-powered
lessons, and multilingual text-to-speech.

OVERVIEW:
LinguaNotebook lets users upload PDF documents and images in any language. The system
automatically parses them into structured markdown using HPD-Parsing (PaddlePaddle —
1B-param hierarchical parallel document parser). All parsed content feeds into an
advanced RAG (Retrieval-Augmented Generation) system with hybrid search. Users create
customizable study schedules, and the system auto-generates daily learning sessions
drawn from their own documents — flashcards, reading comprehension, grammar exercises,
and listening practice — all with multilingual TTS voice playback.

USER JOURNEYS:

1. ONBOARDING & SETUP:
- User signs up via email/password or OAuth (Google, GitHub)
- Selects target language(s) to learn (can choose multiple)
- Self-assesses proficiency level (beginner / intermediate / advanced)
- Sets learning goals (e.g., 10 new words/day, 30 min study/day)
- Uploads first document (textbook PDF, news article, novel, etc.)

2. DOCUMENT UPLOAD & HPD-PARSING:
- User uploads a PDF (supports up to 500MB, 500+ pages)
- System parses every page via HPD-Parsing pipeline:
  - PyMuPDF renders each PDF page → PIL Image
  - Dynamic tiling: 448×448 tiles (max 24 per page) for the InternViT vision encoder
  - Hierarchical parallel decoding: parent layout branch + concurrent content branches
  - Special tokens <FORK> and <CHILD> orchestrate the parallel generation
  - Output: structured markdown with <BLOCK> tags, bounding boxes, and content types
- Real-time progress displayed via SSE (Server-Sent Events): page count, ETA, speed
- Parsed output saved as markdown files + chunked embeddings in vector database
- User can view, edit, tag, and organize parsed content

3. RAG-POWERED KNOWLEDGE BASE:
- All parsed content is intelligently chunked by block type (headers, paragraphs, tables, lists)
- Embeddings generated via multilingual model (BGE-M3, 1024-dim, 100+ languages)
- Stored in Qdrant vector database with rich metadata: language, block_type, difficulty, tags
- Hybrid search combines: dense vector similarity + sparse BM25 keyword + metadata filtering
- Incremental indexing: new PDF uploads automatically update the RAG index without rebuilding
- User can search across all their documents by concept, keyword, or content type

4. CUSTOMIZABLE STUDY SCHEDULE:
- User creates a study schedule specifying:
  - Time of day (e.g., 7:00–7:30 AM)
  - Days of the week (Mon/Wed/Fri or daily)
  - Preferred content types (vocabulary, grammar, reading, listening)
  - Daily lesson size (number of new items per session)
- System auto-matches RAG content to schedule parameters
- Integrated Spaced Repetition System (SM-2 algorithm):
  - Previously learned items are automatically scheduled for review
  - Difficulty adapts based on user performance (ease factor, interval, repetitions)
  - Review cards interleaved with new content in each session

5. DAILY LEARNING SESSION:
- Each day, the system generates a complete learning session from RAG + schedule:
  - Vocabulary Flashcards: word/term, definition, example sentence from source doc, pronunciation
  - Reading Comprehension: passage from the user's own document + multiple-choice questions
  - Grammar Exercises: grammar patterns extracted from the text with fill-in-the-blank
  - Listening Practice: TTS reads a passage aloud, user answers comprehension questions
- Every content item has a play button for TTS voice playback
- Waveform visualization animates during audio playback
- User can choose voice (male/female), speed (0.5x–2x), and language per item
- Session results are scored and fed back into SRS for adaptive scheduling

6. TEXT-TO-SPEECH (TTS) SYSTEM:
- Multi-language support: English, Vietnamese, Chinese, Japanese, Korean, French, German, Spanish
- Edge TTS as primary engine (free, cloud-based, neural quality)
- Piper TTS as offline fallback (local, no internet required)
- Audio caching: Redis stores generated audio bytes with 30-day TTL
- Waveform visualization: real-time canvas-based waveform using wavesurfer.js
- Granular playback: play single word, single sentence, or full paragraph
- Downloadable audio: user can export audio files for offline listening

7. PROGRESS DASHBOARD & ANALYTICS:
- Dashboard displays:
  - Current daily streak (consecutive days studied) with calendar heatmap
  - Vocabulary growth: words learned vs. total words in library
  - Cumulative study time with daily/weekly/monthly breakdown
  - Performance charts: accuracy by content type (vocab, reading, grammar, listening)
  - Strengths & weaknesses: auto-identified from SRS performance data
- Export learning report as PDF
- Optional: daily study reminder via email notification

8. PREMIUM TIERS & MONETIZATION:
- Free tier: 5 PDFs, 100MB/file max, 1 target language, basic TTS (2 voices), basic SRS
- Pro tier ($9.99/month): Unlimited PDFs, 500MB/file, all languages, advanced TTS (10+ voices,
  speed control), advanced SRS with analytics, PDF report export, ad-free
- Team tier ($29.99/month): All Pro features + team dashboard, shared document library,
  admin panel with member management, priority support
- Payment via Stripe: subscription management, invoicing, webhook handling

FUNCTIONAL REQUIREMENTS:

FR-001: System MUST allow user registration and login via email/password AND OAuth
        (Google, GitHub)
FR-002: System MUST support PDF uploads up to 500MB and automatically parse them into
        structured markdown
FR-003: System MUST use HPD-Parsing for document parsing: PDF render → PIL Image →
        dynamic tiling (448×448) → hierarchical parallel decoding → structured markdown
        with <BLOCK> tags and bounding boxes
FR-004: System MUST display real-time parsing progress via SSE (Server-Sent Events)
        showing: current page, total pages, elapsed time, ETA, pages per second
FR-005: System MUST intelligently chunk parsed content by block type and generate
        multilingual embeddings
FR-006: System MUST store embeddings in Qdrant vector database with hybrid search
        (dense vector + sparse BM25 + metadata filtering)
FR-007: System MUST incrementally update the RAG index when new documents are uploaded
        (no full re-indexing required)
FR-008: Users MUST be able to create customizable study schedules with: time of day,
        days of week, content type preferences, and daily session size
FR-009: System MUST auto-generate daily learning sessions combining new content from
        RAG and review items from SRS
FR-010: System MUST integrate a Spaced Repetition System using the SM-2 algorithm
        (ease factor, interval, repetitions, next review date)
FR-011: System MUST support multilingual TTS (minimum 8 languages) via Edge TTS
        (primary) and Piper TTS (offline fallback)
FR-012: System MUST cache generated TTS audio (Redis, 30-day TTL) to avoid
        redundant API calls
FR-013: System MUST display real-time waveform visualization during audio playback
FR-014: System MUST provide a progress dashboard showing: streaks (with heatmap),
        vocabulary learned, study time, accuracy charts by content type
FR-015: System MUST support tiered accounts (Free / Pro / Team) with Stripe
        subscription billing and automatic feature gating
FR-016: System MUST enforce strict user data isolation: each user accesses only
        their own documents, schedules, and learning data
FR-017: System MUST support responsive design for desktop (1024px+) and mobile
        (320px+), mobile-first approach
FR-018: System MUST support dark mode and light mode with system preference detection
FR-019: Users MUST be able to view, edit, tag, and organize parsed document content
FR-020: System MUST support exporting learning progress reports as PDF

USER STORIES (prioritized, each independently testable):

### User Story 1 — Document Upload & HPD-Parsing (Priority: P1) 🎯 MVP

As a language learner, I want to upload my foreign-language PDF textbook and have the
system automatically parse every page into structured, searchable text so I can learn
directly from my own study materials.

Why this priority: This is the foundation — without parsed documents, there is no content
for RAG, no lessons, no flashcards. The entire value proposition starts here.

Independent Test: Upload a 10-page PDF → watch real-time parsing progress via progress bar
→ receive structured markdown output with correct headers, paragraphs, and tables identified.
Can be fully tested by uploading a PDF and verifying the parsed output.

Acceptance Scenarios:
1. Given a logged-in user, When they upload a valid PDF (under 500MB), Then the system
   starts parsing and streams real-time progress via SSE (page X of Y, ETA, speed)
2. Given a parsing job in progress, When the user views the progress bar, Then they see
   current page number, total pages, elapsed time, estimated time remaining, and errors
   (if any) updated in real-time
3. Given a completed parsing job, When the user views the results, Then each page shows
   structured markdown with <BLOCK> tags identifying headers, paragraphs, tables, and
   bounding box coordinates
4. Given a parsing job with a corrupted page, When that page fails, Then the error is
   recorded with the page number and error message, and parsing continues with remaining pages
5. Given a user uploads a PDF in Vietnamese/French/Japanese/Chinese, When parsing completes,
   Then the text content is correctly recognized in the source language with proper character
   encoding (UTF-8)

---

### User Story 2 — RAG Knowledge Base (Priority: P1) 🎯 MVP

As a language learner, I want all my parsed documents to be stored in an intelligent
knowledge base so I can search for any word, phrase, or concept across all my materials
and get contextually relevant results.

Why this priority: RAG is the engine that powers every learning interaction. Without
searchable, retrievable content, the system cannot generate lessons, flashcards, or quizzes.

Independent Test: Upload and parse 3 PDFs → content is automatically chunked and embedded
→ search for a word → get ranked results from all 3 documents with surrounding context.
Can be tested with: upload → wait for indexing → search query → verify results.

Acceptance Scenarios:
1. Given parsed document content, When chunking runs automatically, Then content is split
   into semantically meaningful chunks preserving headers, full tables, and coherent paragraphs
2. Given chunked content, When embedding generation runs, Then each chunk receives a
   BGE-M3 embedding (1024-dim) and is stored in Qdrant with metadata (language, block_type,
   difficulty, document_id, page_number)
3. Given a user searches for a keyword, When the hybrid search executes, Then results
   include both vector-similarity matches AND BM25 keyword matches, ranked by relevance,
   returned in under 1 second for 10,000+ chunks
4. Given an existing RAG index, When a user uploads a new PDF, Then only the new document's
   chunks are embedded and added to the index — existing chunks are not reprocessed

---

### User Story 3 — Study Schedule & Daily Lessons (Priority: P1) 🎯 MVP

As a language learner, I want to set my study schedule (when, how often, what to focus on)
and receive an auto-generated daily lesson drawn from my own documents so I can maintain
a consistent learning habit.

Why this priority: This is the core user-facing loop — schedule + auto-generated lessons
is what the user interacts with every day. Combined with US1+US2, this completes the MVP.

Independent Test: Create a schedule (e.g., Mon/Wed/Fri at 8am, focus on vocabulary from
French textbook) → system generates a daily lesson with flashcards, reading passage, and
quiz questions → complete the lesson → see results. Can be tested by creating a schedule
and verifying lesson generation.

Acceptance Scenarios:
1. Given a logged-in user, When they create a schedule with days, time, duration, and content
   preferences, Then the schedule is saved and the system begins generating daily lessons
2. Given an active schedule, When the system generates a daily lesson, Then the lesson
   contains: vocabulary flashcards (with definitions and source-document examples), a reading
   passage with comprehension questions, and grammar exercises — all sourced from the user's
   RAG knowledge base
3. Given a daily lesson, When the user completes all items, Then a score is calculated,
   completed items feed into SRS, and the lesson is marked as done for that day
4. Given a user changes their schedule, When the next daily lesson is generated, Then it
   reflects the new preferences (content types, duration, difficulty)

---

### User Story 4 — TTS Voice & Audio System (Priority: P2)

As a language learner, I want to hear any word, sentence, or passage spoken aloud with
natural pronunciation so I can practice listening comprehension and improve my accent.

Why this priority: Listening is a core language skill. This enhances all three P1 stories
by adding audio to flashcards, reading passages, and quizzes. However, the core learning
loop (upload → parse → RAG → lessons) works without it.

Independent Test: Open any flashcard or reading passage → click the play button → hear
natural TTS audio within 2 seconds → see waveform animation → switch language/voice/speed.
Can be tested by playing audio from any content item.

Acceptance Scenarios:
1. Given a text content item (word, sentence, or paragraph), When the user clicks play,
   Then audio plays within 2 seconds (with cache) using the configured voice and language
2. Given audio is playing, When the user views the waveform, Then a real-time animated
   waveform visualization is displayed tracking the audio progress
3. Given the audio player, When the user changes voice (male/female), speed (0.5x-2x),
   or language, Then subsequent playback uses the new settings
4. Given TTS has been generated for a text, When the same text is played again, Then the
   cached audio is served from Redis (no external API call, <100ms response)
5. Given the user is offline, When they play a previously cached audio item, Then Piper TTS
   fallback generates audio locally without internet

---

### User Story 5 — Spaced Repetition System (Priority: P2)

As a language learner, I want the system to automatically schedule vocabulary review using
spaced repetition so I retain what I've learned with minimal effort.

Why this priority: SRS dramatically improves long-term retention but the core learning
loop (P1 stories) already delivers value with one-time learning. SRS makes it stick.

Independent Test: Complete a lesson with 10 flashcards → SRS cards are created with SM-2
parameters → next day, review cards appear in the daily lesson → rate each card (1-5) →
intervals adjust. Can be tested by completing flashcards and verifying review scheduling.

Acceptance Scenarios:
1. Given a user completes a flashcard, When the session ends, Then an SRS card is created
   with SM-2 parameters: ease_factor=2.5, interval=1 day, repetitions=0, next_review=tomorrow
2. Given SRS cards are due for review, When the daily lesson is generated, Then due review
   cards are interleaved with new content items
3. Given a user rates a review card (1=forgot, 5=easy), When the rating is submitted, Then
   the SM-2 algorithm recalculates ease_factor, interval, and next_review_date accordingly
4. Given consistent correct answers, When interval grows, Then review frequency decreases
   (1d → 3d → 7d → 14d → 30d → 60d+) following SM-2 progression

---

### User Story 6 — Progress Dashboard (Priority: P2)

As a language learner, I want a visual dashboard showing my learning progress — streaks,
vocabulary growth, study time, and performance trends — so I stay motivated and see my
improvement over time.

Why this priority: Motivation and visibility are key to retention as a paid user. However,
the core learning functionality works without it.

Independent Test: After studying for several days → open the dashboard → see streak count,
calendar heatmap, vocabulary growth chart, study time breakdown, and accuracy by content type.
Can be tested by generating learning data and verifying dashboard renders correctly.

Acceptance Scenarios:
1. Given a user with 7 consecutive days of completed lessons, When they view the dashboard,
   Then the streak counter shows "7" with a calendar heatmap highlighting studied days
2. Given accumulated learning data, When the dashboard loads, Then charts display: vocabulary
   learned over time (line chart), study minutes by day (bar chart), accuracy by content type
   (radar or grouped bar chart)
3. Given a user clicks "Export Report", When the PDF is generated, Then it contains a summary
   of all dashboard metrics formatted for printing/sharing

---

### User Story 7 — Authentication & User Management (Priority: P3)

As a user, I want to create an account, log in securely, and know that my learning data,
documents, and progress are private and accessible only to me.

Why this priority: Auth is necessary for data isolation and premium tiers, but the core
learning experience could be built as a single-user app first. P3 because it gates
multi-user and monetization.

Independent Test: Register with email → verify email → log in → upload documents → log out
→ log back in → documents and progress are still there. Register with Google OAuth → same
flow. Can be tested by creating accounts and verifying data persistence and isolation.

Acceptance Scenarios:
1. Given a new visitor, When they register with email and password, Then an account is created,
   a verification email is sent, and they cannot access protected routes until verified
2. Given an unverified account, When the user clicks the email verification link, Then the
   account is activated and they are redirected to the onboarding flow
3. Given User A and User B are both logged in, When User A uploads documents, Then User B
   cannot see, search, or access User A's documents under any circumstances
4. Given a user clicks "Delete My Account", When confirmed, Then all user data (documents,
   chunks, schedules, lessons, SRS cards) is permanently deleted within 30 days (GDPR)

---

### User Story 8 — Premium Tiers & Stripe Payments (Priority: P3)

As a user, I want to upgrade to a Pro or Team plan to unlock unlimited documents, advanced
TTS, detailed analytics, and team sharing features.

Why this priority: Monetization is the business goal, but the product must work first.
Build the free tier as MVP, then add payment gating.

Independent Test: Free user clicks "Upgrade to Pro" → enters Stripe payment → subscription
is created → Pro features unlock immediately → billing appears in Stripe dashboard → cancel
→ features revert at period end. Can be tested with Stripe test mode.

Acceptance Scenarios:
1. Given a free-tier user, When they attempt to upload a 6th PDF, Then a feature gate
   displays: "Upgrade to Pro for unlimited PDFs" with a link to the pricing page
2. Given a user on the pricing page, When they select Pro and complete Stripe Checkout,
   Then their account tier updates to "pro" and all Pro features are immediately available
3. Given a Pro subscriber, When their subscription period ends without renewal, Then their
   account reverts to Free tier with feature gates re-applied
4. Given a Team plan admin, When they invite team members via email, Then members can join,
   access the shared document library, and appear in the team dashboard

---

EDGE CASES:

- What happens when a user uploads a PDF that is entirely handwritten (no OCR-able text)?
  → System detects <10% text extraction, warns user, still stores images for reference
- What happens when HPD-Parsing encounters a page with no detectable layout blocks?
  → Page is stored as unstructured text; user can manually tag blocks via the editor
- What happens when the GPU server is at capacity (multiple concurrent parse jobs)?
  → Jobs are queued in Celery with FIFO; user sees "queued" status with position in queue
- What happens when a user's subscription payment fails?
  → Stripe retries up to 3 times over 1 week; on final failure, account reverts to Free tier
- What happens when a user uploads a PDF in a language not supported by TTS?
  → Content is still parsed and usable for reading/writing; TTS shows "language not supported"
    with a suggestion to request it
- How does the system handle a 500-page PDF upload on a slow connection?
  → Chunked upload (resumable) with progress indicator; parsing starts after full upload
- What happens when a user deletes a document that is the source of active SRS cards?
  → User is warned: "X SRS cards depend on this document. Delete anyway?" Cards are orphaned
    but content is retained in the card
- What happens when a daily lesson is scheduled but the user has no new content to learn?
  → Lesson consists entirely of SRS review cards; system suggests uploading new documents

SUCCESS CRITERIA:

SC-001: A user can upload and parse a 100-page PDF in under 5 minutes (on NVIDIA RTX 4090
        or equivalent GPU); under 30 minutes on Intel Arc integrated GPU
SC-002: Parsing accuracy exceeds 90% (measured by correct block type identification rate
        on OmniDocBench v1.6 or similar benchmark)
SC-003: RAG hybrid search returns results in under 1 second for a knowledge base with
        10,000+ chunks
SC-004: A new user can complete onboarding and schedule setup in under 3 minutes
SC-005: 80% of active users maintain a study streak of at least 7 consecutive days
        (measured 30 days post-signup)
SC-006: TTS audio playback starts within 2 seconds of clicking play (with cache hit);
        within 5 seconds (cache miss, Edge TTS)
SC-007: System handles 1,000 concurrent users without degradation (p95 latency <500ms
        for API endpoints)
SC-008: Application achieves Lighthouse score >90 for Performance, Accessibility, Best
        Practices, and SEO
SC-009: Time-to-Interactive under 3 seconds on desktop (4G) and under 5 seconds on
        mobile (4G)
SC-010: Free-to-Pro conversion rate of at least 5% within 90 days of account creation

ASSUMPTIONS:

- Users have stable broadband internet (for uploads, TTS, and online features)
- Users own or have legal rights to the PDF documents they upload
- HPD-Parsing model is deployed on a server with GPU (minimum 8GB VRAM NVIDIA or 16GB Intel Arc)
- Uploaded PDFs are text-based or high-quality scans (handwritten text not supported by HPD)
- Users have basic proficiency in the target language (not absolute beginners — the tool is
  for learners who can already read basic text in the target language)
- Stripe is available in the user's country for payment processing
- Target audience is self-directed learners aged 16+ who already own foreign-language materials
- Mobile support in v1 focuses on the learning session and dashboard; document upload is
  desktop-first (file size considerations)
```

---

## 3️⃣ PLAN PROMPT

Command: `/speckit-plan`

```
Implement LinguaNotebook with a service-oriented architecture optimized for
document parsing, RAG retrieval, adaptive learning, and TTS voice synthesis.

TECHNICAL CONTEXT:

Language/Version: Python 3.11 (backend), TypeScript 5.x (frontend)
Primary Dependencies: FastAPI, Celery, Next.js 14, SQLAlchemy, Qdrant client,
                      HuggingFace Transformers 4.x, PyMuPDF, Edge TTS, Piper TTS
Storage: PostgreSQL 15 (relational), Qdrant (vector), Redis (cache/queue),
         S3-compatible object storage (documents/audio)
Testing: pytest + pytest-asyncio (backend), Jest + React Testing Library + Playwright (frontend)
Target Platform: Web (desktop + mobile responsive), Docker containers, cloud deploy
Project Type: Web application (SPA frontend + REST API backend + background workers)
Performance Goals: PDF parsing <5min/100pages (GPU), RAG search <1s for 10K chunks,
                   TTS playback <2s cached, API p95 <500ms
Constraints: GPU required for HPD-Parsing (min 8GB VRAM), memory <16GB per service,
             offline-capable for TTS and learning session
Scale/Scope: 1,000 concurrent users, 10K+ document chunks per user, 8+ languages

PROJECT STRUCTURE:

```
lingua-notebook/
├── backend/
│   ├── src/
│   │   ├── api/                     # FastAPI route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py              # POST /auth/register, /auth/login, /auth/refresh
│   │   │   ├── documents.py         # POST /documents/upload, GET /documents/{id}/parse/progress
│   │   │   │                       # GET /documents, GET /documents/{id}, PATCH /documents/{id}
│   │   │   │                       # DELETE /documents/{id}
│   │   │   ├── learning.py          # POST /schedules, GET /schedules, GET /lessons/daily
│   │   │   │                       # POST /lessons/{id}/complete, GET /lessons/history
│   │   │   ├── rag.py               # GET /rag/search?q=&lang=&type=, GET /rag/chunks/{id}
│   │   │   ├── tts.py               # POST /tts/synthesize, GET /tts/voices, GET /tts/audio/{hash}
│   │   │   ├── progress.py          # GET /progress/dashboard, GET /progress/stats
│   │   │   │                       # GET /progress/export-report
│   │   │   └── payments.py          # POST /payments/create-checkout, POST /payments/webhook
│   │   │                           # GET /payments/subscription
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Declarative base, timestamps mixin
│   │   │   ├── user.py              # User, UserTier enum
│   │   │   ├── document.py          # Document, DocumentStatus enum, ParsedBlock, BlockType enum
│   │   │   ├── schedule.py          # Schedule, ContentType enum
│   │   │   ├── learning.py          # Lesson, LessonStatus enum, LessonItem, ItemType enum
│   │   │   ├── srs.py               # SRSCard
│   │   │   └── payment.py           # Subscription, PlanTier enum
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── parser_service.py    # PDFParser: PyMuPDF → HPD → structured markdown
│   │   │   ├── chunker_service.py   # Smart chunker by block type
│   │   │   ├── embed_service.py     # BGE-M3 embedding generation + Qdrant upsert
│   │   │   ├── rag_service.py       # Hybrid search: dense + sparse + metadata
│   │   │   ├── schedule_service.py  # Schedule CRUD + lesson generation engine
│   │   │   ├── tts_service.py       # TTS orchestration: Edge TTS primary, Piper fallback
│   │   │   ├── srs_service.py       # SM-2 algorithm implementation
│   │   │   ├── payment_service.py   # Stripe integration: checkout, webhooks, sync
│   │   │   └── progress_service.py  # Dashboard aggregation + PDF report generation
│   │   ├── workers/                 # Celery background task definitions
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py        # Celery instance, broker config, task routes
│   │   │   ├── parse_worker.py      # parse_pdf_task: long-running PDF parsing
│   │   │   ├── embed_worker.py      # embed_document_task: chunk + embed + index
│   │   │   └── lesson_worker.py     # generate_daily_lessons_task: nightly batch job
│   │   ├── core/                    # Cross-cutting infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Pydantic Settings: env vars, secrets, feature flags
│   │   │   ├── security.py          # JWT creation/validation, OAuth flows, password hashing
│   │   │   ├── database.py          # AsyncSession factory, engine, connection pool
│   │   │   ├── storage.py           # S3/local file storage abstraction
│   │   │   └── dependencies.py      # FastAPI dependency injection (get_db, get_current_user)
│   │   └── utils/                   # Utility modules
│   │       ├── __init__.py
│   │       ├── hpd_parser.py        # HPD-Parsing wrapper (PDF → markdown per HPD-PARSING-GUIDE)
│   │       ├── chunker.py           # Block-type-aware text chunking
│   │       └── audio_cache.py       # Redis audio cache with hash-based keys
│   ├── alembic/                     # Database migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── contract/                # API contract tests (pytest + httpx)
│   │   │   ├── test_auth_api.py
│   │   │   ├── test_documents_api.py
│   │   │   ├── test_learning_api.py
│   │   │   ├── test_rag_api.py
│   │   │   ├── test_tts_api.py
│   │   │   └── test_progress_api.py
│   │   ├── integration/             # Service integration tests
│   │   │   ├── test_parser_pipeline.py    # PDF → parse → markdown
│   │   │   ├── test_rag_pipeline.py       # markdown → chunk → embed → search
│   │   │   ├── test_lesson_generation.py  # schedule + RAG → daily lesson
│   │   │   ├── test_srs_workflow.py       # complete lesson → SRS → review schedule
│   │   │   └── test_tts_pipeline.py       # text → TTS → cache → playback
│   │   └── unit/                    # Unit tests
│   │       ├── test_chunker.py
│   │       ├── test_srs_algorithm.py
│   │       ├── test_hpd_parser.py
│   │       └── test_audio_cache.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── app/                     # Next.js 14 App Router
│   │   │   ├── layout.tsx           # Root layout: providers, theme, fonts
│   │   │   ├── page.tsx             # Landing/marketing page
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── (dashboard)/
│   │   │   │   ├── layout.tsx       # Authenticated layout with sidebar nav
│   │   │   │   └── page.tsx         # Main dashboard
│   │   │   ├── documents/
│   │   │   │   ├── page.tsx         # Document list with upload dropzone
│   │   │   │   ├── [id]/page.tsx    # Document viewer/editor
│   │   │   │   └── upload/page.tsx  # Upload page with progress
│   │   │   ├── learning/
│   │   │   │   ├── page.tsx         # Today's lesson (or "no lesson scheduled")
│   │   │   │   └── [id]/page.tsx    # Individual lesson session
│   │   │   ├── schedule/
│   │   │   │   └── page.tsx         # Schedule builder/editor
│   │   │   ├── progress/
│   │   │   │   └── page.tsx         # Full progress dashboard
│   │   │   ├── settings/
│   │   │   │   └── page.tsx         # User settings, preferences
│   │   │   └── premium/
│   │   │       └── page.tsx         # Pricing page, upgrade flow
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui primitives (button, card, input, etc.)
│   │   │   ├── document/
│   │   │   │   ├── DocumentUploader.tsx    # Drag-and-drop PDF upload
│   │   │   │   ├── ParseProgress.tsx       # Real-time SSE progress bar + stats
│   │   │   │   ├── DocumentViewer.tsx      # Rendered markdown with block types
│   │   │   │   └── DocumentEditor.tsx      # Edit/tag parsed blocks
│   │   │   ├── learning/
│   │   │   │   ├── Flashcard.tsx           # Flip card: term → definition + example
│   │   │   │   ├── ReadingPassage.tsx      # Passage + comprehension questions
│   │   │   │   ├── GrammarExercise.tsx     # Fill-in-the-blank grammar
│   │   │   │   ├── ListeningExercise.tsx   # TTS audio + questions
│   │   │   │   └── SessionProgress.tsx     # Progress ring during session
│   │   │   ├── tts/
│   │   │   │   ├── AudioPlayer.tsx         # Play/pause/speed/voice controls
│   │   │   │   └── Waveform.tsx            # Canvas-based waveform visualization
│   │   │   ├── schedule/
│   │   │   │   ├── ScheduleBuilder.tsx     # Drag-and-drop schedule builder
│   │   │   │   └── WeeklyCalendar.tsx      # Weekly schedule overview
│   │   │   └── dashboard/
│   │   │       ├── StreakWidget.tsx        # Streak counter + heatmap
│   │   │       ├── VocabChart.tsx          # Vocabulary growth chart
│   │   │       ├── StudyTimeChart.tsx      # Study time breakdown
│   │   │       └── AccuracyChart.tsx       # Accuracy by content type
│   │   ├── hooks/
│   │   │   ├── useSSE.ts             # SSE hook for real-time parse progress
│   │   │   ├── useTTS.ts             # TTS playback hook
│   │   │   ├── useAuth.ts            # Auth state hook
│   │   │   └── useRAG.ts             # RAG search hook
│   │   ├── lib/
│   │   │   ├── api.ts                # Axios/fetch API client with auth interceptors
│   │   │   ├── stripe.ts             # Stripe client-side helpers
│   │   │   └── utils.ts              # Shared utilities
│   │   └── styles/
│   │       └── globals.css           # Tailwind directives + CSS variables
│   ├── public/
│   │   ├── icons/                    # App icons, favicon
│   │   └── audio/                    # Default TTS samples
│   ├── tests/
│   │   ├── e2e/                      # Playwright E2E tests
│   │   │   ├── auth.spec.ts
│   │   │   ├── upload-parse.spec.ts
│   │   │   ├── learning-session.spec.ts
│   │   │   └── premium-upgrade.spec.ts
│   │   └── components/               # Component tests
│   │       ├── Flashcard.test.tsx
│   │       └── AudioPlayer.test.tsx
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── docker-compose.yml                # Full stack: backend, frontend, postgres, qdrant, redis,
│                                     # celery-worker (with GPU), celery-beat
├── .github/
│   └── workflows/
│       ├── ci.yml                    # Lint, type-check, test on PR
│       └── deploy.yml                # Build & deploy on merge to main
├── .env.example                      # All environment variables documented
├── README.md
└── Makefile                          # Common commands: dev, test, build, migrate
```

PHASE 0 — RESEARCH TOPICS (resolve all NEEDS CLARIFICATION):

1. HPD-Parsing Service Integration:
   - How to wrap the 2GB HPD model in a long-lived FastAPI service process
   - VRAM management strategy for concurrent parse requests (queue vs. batching)
   - Multi-GPU support or GPU-less graceful degradation path
   - Cold-start optimization: model preloading, weights in shared memory

2. Qdrant Schema & Hybrid Search:
   - Optimal collection design: per-user collections vs. single collection with
     user-id payload filtering (security + performance trade-off)
   - Sparse vector generation: BM25 at index time vs. query time
   - Metadata filter pushdown: which filters apply before vs. after vector search
   - Quantization strategy: scalar vs. product quantization for 10K+ chunks/user

3. Smart Chunking Strategy:
   - Block-type-aware chunking based on HPD output (<BLOCK>header, <BLOCK>table,
     <BLOCK>paragraph, <BLOCK>list)
   - Semantic boundary detection for paragraph splitting (sentence boundaries,
     topic shifts)
   - Optimal chunk size for language learning: smaller for vocabulary (1-3 sentences),
     larger for reading comprehension (1-3 paragraphs)
   - Chunk overlap strategy for context preservation across chunk boundaries

4. Multilingual Embedding Model Selection:
   - BGE-M3 vs. multilingual-e5-large vs. LaBSE: accuracy benchmarks on multilingual
     retrieval tasks
   - Inference performance: tokens/sec on CPU vs. GPU, batch size optimization
   - Dimension trade-off: 768 vs. 1024 vs. 2048 (storage × recall quality)
   - Fine-tuning feasibility on domain-specific language-learning corpus

5. TTS Pipeline Comparison:
   - Edge TTS: latency, voice quality per language, rate limits, reliability
   - Piper TTS: model size per language (50-100MB each), quality vs. Edge TTS,
     CPU inference time
   - Coqui TTS / XTTS v2: quality, multi-language support, GPU requirements
   - Caching strategy: hash-based Redis keys, TTL policy, cache warming for
     scheduled lessons

6. Spaced Repetition SM-2 Implementation:
   - Standard SM-2 parameters (ease factor, interval, repetitions) and their
     calibration for language learning vocabulary
   - Handling overdue reviews: catch-up scheduling algorithm
   - Integration with daily lesson generation: new content × review ratio
   - Anki-like modifications: graduating interval, lapse handling, leech detection

7. Stripe Payment Integration:
   - Checkout Session vs. Payment Links for subscription setup
   - Webhook event handling: checkout.session.completed, customer.subscription.updated,
     customer.subscription.deleted, invoice.payment_failed
   - Idempotency: handling duplicate webhook events
   - Subscription lifecycle: trial period, upgrade/downgrade (proration), cancellation
     (immediate vs. end-of-period)

8. Deployment Architecture & Cost Estimation:
   - Vercel (frontend) + Railway (backend API) + dedicated GPU instance (parser worker)
   - AWS alternative: ECS Fargate (API) + EC2 G5.xlarge (GPU parser) + RDS (Postgres)
     + ElastiCache (Redis)
   - Monthly cost projection at 100, 1,000, 10,000 users
   - Database backup strategy, disaster recovery, and SLA targets

PHASE 1 — DESIGN ARTIFACTS:

1. data-model.md:
   - Full entity-relationship diagram (10 entities with all fields, types, constraints)
   - State machines for: DocumentStatus (uploading→queued→parsing→completed/failed),
     LessonStatus (pending→in_progress→completed), SubscriptionStatus
   - Index recommendations for query patterns
   - Migration strategy: initial schema + forward-only migrations via Alembic

2. contracts/ (OpenAPI 3.1 specs):
   - auth.yaml: POST /auth/register, POST /auth/login, POST /auth/refresh,
     POST /auth/logout, GET /auth/me
   - documents.yaml: POST /documents/upload, GET /documents, GET /documents/{id},
     PATCH /documents/{id}, DELETE /documents/{id},
     GET /documents/{id}/parse/progress (SSE)
   - learning.yaml: POST /schedules, GET /schedules, PATCH /schedules/{id},
     GET /lessons/daily, POST /lessons/{id}/items/{item_id}/answer,
     POST /lessons/{id}/complete
   - rag.yaml: GET /rag/search, GET /rag/chunks/{id}, GET /rag/stats
   - tts.yaml: POST /tts/synthesize, GET /tts/voices, GET /tts/audio/{hash}
   - progress.yaml: GET /progress/dashboard, GET /progress/export-report
   - payments.yaml: POST /payments/create-checkout-session,
     POST /payments/webhook, GET /payments/subscription

3. quickstart.md:
   - Prerequisites: Python 3.11, Node.js 20, Docker Desktop, GPU with 8GB+ VRAM
   - `cp .env.example .env` and fill in required values
   - `docker compose up -d` (starts postgres, qdrant, redis)
   - Backend: `cd backend && python -m venv .venv && pip install -r requirements.txt`
   - `cd backend && alembic upgrade head && uvicorn src.main:app --reload`
   - Frontend: `cd frontend && npm install && npm run dev`
   - Run tests: `cd backend && pytest`, `cd frontend && npm test`
   - Seed data: `python scripts/seed.py` (creates test user, sample PDF, demo schedule)
```

---

## 4️⃣ TASKS PROMPT

Command: `/speckit-tasks`

```
Generate actionable, dependency-ordered tasks for LinguaNotebook based on the
feature spec (spec.md) and implementation plan (plan.md).

ORGANIZATION RULES:
- Tasks grouped by User Story (US1–US8) so each story is independently implementable
  and testable
- [P] marker for tasks that can run in parallel (different files, no shared state)
- [USx] label maps each task to its user story for traceability
- Test-first: every implementation phase starts with contract/integration tests written
  BEFORE the code (tests must FAIL first, then pass after implementation)
- Every task includes the exact file path to create or modify

PHASE STRUCTURE:
- Phase 1: Project Setup & Scaffolding
- Phase 2: Foundational Infrastructure (BLOCKS all user stories)
- Phase 3: US1 (P1) — Document Upload & HPD-Parsing 🎯 MVP
- Phase 4: US2 (P1) — RAG Knowledge Base 🎯 MVP
- Phase 5: US3 (P1) — Study Schedule & Daily Lessons 🎯 MVP
- Phase 6: US4 (P2) — TTS Voice & Audio System
- Phase 7: US5 (P2) — Spaced Repetition System
- Phase 8: US6 (P2) — Progress Dashboard
- Phase 9: US7 (P3) — Authentication & User Management
- Phase 10: US8 (P3) — Premium Tiers & Stripe Payments
- Phase 11: Cross-Cutting Polish (responsive, dark mode, PWA, performance, security)

For each phase, generate specific tasks following the pattern:
- Setup tasks → Foundational tasks → [Story] Test tasks → [Story] Model tasks →
  [Story] Service tasks → [Story] API endpoint tasks → [Story] Frontend tasks →
  Checkpoint validation

IMPORTANT: Ensure that after Phase 3 (US1), there is a working MVP where a user can
upload a PDF, watch parsing progress, and view the structured markdown output.
After Phase 5 (US3), the full core learning loop should be functional end-to-end.
```

---

## 5️⃣ IMPLEMENT PROMPT

Command: `/speckit-implement`

```
Execute the complete LinguaNotebook implementation by processing all tasks in tasks.md
in dependency order. Follow these critical implementation guidelines:

═══════════════════════════════════════════════════════════════
1. TEST-FIRST DEVELOPMENT (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════
- Write contract tests FIRST → verify they FAIL → then implement
- Write integration tests for service pipelines → verify they FAIL → then implement
- Write unit tests for utilities → verify they FAIL → then implement
- Every API endpoint MUST have a corresponding contract test
- Run full test suite after each phase checkpoint

═══════════════════════════════════════════════════════════════
2. HPD-PARSING INTEGRATION (CRITICAL PATH)
═══════════════════════════════════════════════════════════════
Implement EXACTLY per the HPD-PARSING-GUIDE.md at:
C:\Users\ASUS\Downloads\HPD-Parsing\HPD-PARSING-GUIDE.md

Key implementation rules:
- Model: PaddlePaddle/HPD-Parsing from HuggingFace (1B params, ~2GB VRAM)
- Load with: AutoModel.from_pretrained(model_dir, trust_remote_code=True,
  dtype=torch.bfloat16, attn_implementation='eager')
- Tokenizer: AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True,
  use_fast=False) ← use_fast=False is CRITICAL
- Call model.load_mtp_weights() once after loading (enables P-MTP speculative decoding)
- PDF rendering: PyMuPDF (fitz) — render each page to PIL Image via pix.samples
- DPI: 100 default (general docs), 150 (dense text/tables/formulas)
- Dynamic tiling: image_preprocess.py → 448×448 tiles, max 24 per page
- HPD inference: model.generate_hpd() with use_mtp=True, num_speculative_tokens=6
- Memory management: del pixel_values after each page, torch.cuda.empty_cache()
  (or torch.xpu.empty_cache()) every 10 pages
- Progress: emit page number, elapsed time, ETA, pages/sec via callback → SSE
- Run parsing in a dedicated Celery worker with GPU access
- Model stays loaded (~2GB constant), results stored as strings (~2KB/page)
- Handle errors per-page: log the error, continue with next page, don't abort the book
- Use model.eval() and torch.no_grad() for all inference
- Python version: 3.10–3.12 (NOT 3.13+)
- Transformers version: >=4.46,<5 (NOT 5.x — all_tied_weights_keys incompatibility)

═══════════════════════════════════════════════════════════════
3. RAG PIPELINE
═══════════════════════════════════════════════════════════════
- Smart chunker: Parse HPD <BLOCK> tags to identify block type
  - Headers: keep intact as standalone chunks
  - Tables: keep intact, convert to structured text
  - Paragraphs: split at sentence boundaries, 3-5 sentences per chunk,
    1-sentence overlap
  - Lists: keep intact as standalone chunks
- Embeddings: BGE-M3 via sentence-transformers or FlagEmbedding
  - model_name: "BAAI/bge-m3", dimension: 1024
  - Batch processing (32 chunks per batch) for efficiency
- Qdrant collection per user (strong data isolation) with schema:
  - vectors: {dense: 1024-dim float, sparse: BM25 sparse vector}
  - payload: {user_id, document_id, block_type, language, difficulty, page_number,
    chunk_index, token_count, created_at}
- Hybrid search: combine dense score + BM25 score with configurable fusion (RRF default)
- Incremental indexing: on new PDF upload, only embed and index new chunks
- Re-indexing: support PATCH /documents/{id} for edited content → re-embed affected chunks

═══════════════════════════════════════════════════════════════
4. TTS VOICE SYSTEM
═══════════════════════════════════════════════════════════════
- Primary engine: Edge TTS (edge-tts Python package)
  - Free, neural quality, 100+ voices across 30+ languages
  - Async interface: await communicate() → audio bytes
- Fallback engine: Piper TTS (piper-tts Python package + ONNX runtime)
  - Local inference, no internet required
  - Download voice models on-demand (~50-100MB per language/voice)
  - Languages: EN, VI, ZH, JA, KO, FR, DE, ES (minimum)
- Audio caching in Redis:
  - Key format: tts:{engine}:{lang}:{voice}:{sha256(text)}
  - Value: WAV/MP3 bytes (base64 encoded)
  - TTL: 30 days
  - Max cache size: 5GB per user (configurable)
- Cache warming: pre-generate TTS for tomorrow's lesson during off-peak hours
- Frontend: wavesurfer.js for waveform visualization
- AudioPlayer component: play/pause, seek, speed (0.5x–2x), voice selector,
  download button

═══════════════════════════════════════════════════════════════
5. FRONTEND IMPLEMENTATION
═══════════════════════════════════════════════════════════════
- Next.js 14 App Router with React Server Components where possible
  - Server Components for data fetching (document list, dashboard stats)
  - Client Components for interactive elements (flashcards, audio player, upload)
- Styling: Tailwind CSS + shadcn/ui component library
  - Dark mode: next-themes with system preference detection
  - Responsive: mobile-first, breakpoints at sm(640), md(768), lg(1024), xl(1280)
- State management: React Context + SWR for server state (caching, revalidation)
- SSE client: EventSource API for real-time parsing progress
- PWA: next-pwa for offline-capable learning session (service worker caches
  lesson content + TTS audio)
- Error boundaries at page and component level
- Loading states: skeletons for every data-dependent view
- Empty states: helpful messages guiding the user to the next action

═══════════════════════════════════════════════════════════════
6. DEPLOYMENT READINESS
═══════════════════════════════════════════════════════════════
- Docker Compose for local development:
  - backend (FastAPI + uvicorn, hot reload)
  - celery-worker (GPU passthrough)
  - celery-beat (scheduled task: generate daily lessons)
  - frontend (Next.js dev server)
  - postgres (port 5432)
  - qdrant (port 6333)
  - redis (port 6379)
- CI/CD: .github/workflows/ci.yml
  - Lint: ruff (backend), eslint + prettier (frontend)
  - Type check: mypy (backend strict), tsc (frontend)
  - Test: pytest (backend), Jest + Playwright (frontend)
  - Build: Docker images tagged with git SHA
- .github/workflows/deploy.yml
  - On merge to main: build → push images → deploy
- Health check endpoints:
  - GET /health (API alive)
  - GET /health/ready (DB + Redis + Qdrant + GPU reachable)
- Environment variables: all config via .env, documented in .env.example
- Rate limiting: slowapi or external (Redis-based token bucket, 100 req/min per user)
- Structured logging: structlog (JSON format, correlation IDs per request)
```

---

## 📋 HOW TO USE

### Method 1: Manual (step by step with review gates)

Copy each prompt block above and paste it into Claude Code after typing the corresponding
slash command:

```
/speckit-constitution
[paste Constitution prompt from Section 1]

/speckit-specify
[paste Specify prompt from Section 2]

/speckit-clarify     ← optional, run after specify if spec has [NEEDS CLARIFICATION]

/speckit-plan
[paste Plan prompt from Section 3]

/speckit-checklist   ← optional, run after plan for quality gates

/speckit-tasks
[paste Tasks prompt from Section 4]

/speckit-analyze     ← optional, run after tasks before implement

/speckit-implement
[paste Implement prompt from Section 5]

/speckit-converge    ← run after implement to catch remaining work
```

### Method 2: Automated workflow (single command)

```bash
specify workflow run speckit --args "Build LinguaNotebook — a production-grade language learning web app with HPD-Parsing document ingestion, advanced RAG knowledge base, customizable study schedules with spaced repetition, daily auto-generated lessons, and multilingual TTS voice system. Supports Free/Pro/Team tiers with Stripe payments."
```

The workflow runs: specify → plan → tasks → implement with review gates between each step.

---

## 📎 Key Reference

HPD-Parsing implementation guide: `C:\Users\ASUS\Downloads\HPD-Parsing\HPD-PARSING-GUIDE.md`

Critical implementation takeaways from the guide:

| Aspect | Detail |
|--------|--------|
| Model | PaddlePaddle/HPD-Parsing, 1B params, ~2GB VRAM in bf16 |
| Architecture | InternViT vision encoder (448×448 tiles, max 24) + Qwen3-0.6B LLM |
| Special tokens | `<FORK>` (spawns child branch), `<CHILD>` (marks child content) |
| PDF → Markdown pipeline | PyMuPDF render → PIL Image → Dynamic tiling → HPD inference → Structured markdown |
| DPI settings | 72 (fast test), 100 (general, default), 150 (dense text/tables), 200 (small text) |
| Speed (RTX 4090) | ~3-5s per page, ~10-17 min for 200-page book |
| Speed (Intel Arc) | ~20-25s per page, ~66-83 min for 200-page book |
| Memory management | Delete tensors after each page; empty GPU cache every 10 pages |
| Key constraints | Python 3.10–3.12, transformers>=4.46<5, use_fast=False, attn_implementation='eager' |
| Progress tracking | SSE (Server-Sent Events) with page count, ETA, pages/sec |
| Output format | `<BLOCK>type [x1,y1,x2,y2]<CHILD>content` |
| Language support | Multilingual via Qwen3 tokenizer (151,681 vocab): EN, VI, ZH, JA, KO, EU languages |

---

## ✅ Pre-Flight Checklist

- [x] `specify-cli` v0.14.2 installed and verified
- [x] `specify init --here --integration claude` completed
- [x] HPD-PARSING-GUIDE.md read and understood
- [ ] GPU with ≥8GB VRAM available (or cloud GPU access configured)
- [ ] Python 3.11+ environment ready
- [ ] Node.js 20+ environment ready
- [ ] Docker Desktop installed and running
- [ ] Stripe account created (test mode for development)
- [ ] Vercel account (frontend deploy) + Railway/AWS account (backend deploy)
- [ ] HuggingFace account (to download HPD-Parsing model)
