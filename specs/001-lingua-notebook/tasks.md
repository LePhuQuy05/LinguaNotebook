# Tasks: LinguaNotebook

**Input**: Design documents from `specs/001-lingua-notebook/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.yaml
**Tests**: Test-first development per constitution §VI. Contract tests written BEFORE implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US11)
- Every task includes exact file paths

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, monorepo scaffolding, Docker, CI/CD

- [x] T001 Create monorepo root with pnpm workspace config: `pnpm-workspace.yaml`, `turbo.json`, `.env.example`, `Makefile`
- [x] T002 [P] Initialize backend Python project: `backend/pyproject.toml`, `backend/requirements.txt`, `backend/src/__init__.py`
- [x] T003 [P] Initialize frontend Next.js project with TypeScript, Tailwind, shadcn/ui: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/next.config.js`
- [x] T004 [P] Initialize mobile React Native + Expo project: `mobile/package.json`, `mobile/app.json`, `mobile/tsconfig.json`
- [x] T005 [P] Initialize shared TypeScript package: `shared/package.json`, `shared/tsconfig.json`, `shared/src/types/`, `shared/src/constants/`
- [x] T006 [P] Create Docker Compose dev stack with postgres, qdrant, redis, minio: `docker/docker-compose.yml`
- [x] T007 [P] Configure GitHub Actions CI pipeline: `.github/workflows/ci.yml` (lint, type-check, test, build)
- [x] T008 [P] Create README.md with project description, quickstart, badges; LICENSE (MIT); CONTRIBUTING.md; CODE_OF_CONDUCT.md
- [x] T009 Install ui-ux-pro-max design tokens into frontend: copy `design-system/linguanotebook/tokens.css` → `frontend/src/styles/tokens.css`; configure `tailwind.config.ts` from `design-system/linguanotebook/tailwind.config.ts`
- [x] T010 Run `git init`, create `.gitignore` for Python, Node, Docker artifacts. Initial commit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work begins until this phase is complete

### Backend Foundation

- [x] T011 Setup FastAPI application with CORS, error handlers, health endpoints: `backend/src/main.py`, `backend/src/core/config.py`, `backend/src/core/dependencies.py`
- [x] T012 [P] Configure async SQLAlchemy engine, session factory, base model: `backend/src/core/database.py`, `backend/src/models/base.py`
- [x] T013 [P] Configure Redis client and Celery app with task routing: `backend/src/workers/celery_app.py`, `backend/src/core/redis.py`
- [x] T014 [P] Configure Qdrant client with collection management utilities: `backend/src/core/qdrant.py`
- [x] T015 [P] Configure S3/MinIO storage abstraction: `backend/src/core/storage.py`
- [x] T016 Create initial Alembic migration with all 13 entities from data-model.md: `backend/alembic/env.py`, `backend/alembic/versions/001_initial.py`
- [x] T017 [P] Implement JWT token creation/validation and OAuth2 flows (Google, GitHub): `backend/src/core/security.py`
- [x] T018 [P] Setup structured logging with request ID propagation: `backend/src/core/logging.py`

### Frontend Foundation

- [x] T019 Setup Next.js App Router with root layout, providers (theme, auth, query), font loading: `frontend/src/app/layout.tsx`, `frontend/src/app/providers.tsx`
- [x] T020 [P] Create API client with auth interceptor, error handling, SWR configuration: `frontend/src/lib/api.ts`
- [x] T021 [P] Create shared UI primitives from shadcn/ui: button, input, card, dialog, dropdown, tabs, skeleton, toast: `frontend/src/components/ui/`
- [x] T022 [P] Implement dark/light theme toggle with system preference detection and persistence: `frontend/src/lib/theme.ts`

### Shared Package

- [x] T023 Generate TypeScript types from OpenAPI spec (contracts/api.yaml): `shared/src/types/api.ts`
- [x] T024 [P] Define shared constants: languages list, tier-free feature flags, SM-2 defaults, chunk size defaults: `shared/src/constants/index.ts`

**Checkpoint**: Foundation ready — all user stories can now be implemented in parallel

---

## Phase 3: User Story 1 — Document Upload & HPD-Parsing (Priority: P1) 🎯 MVP

**Goal**: User uploads a PDF → system parses it via HPD-Parsing → structured markdown output with real-time SSE progress

**Independent Test**: Upload a 10-page PDF → watch real-time parsing progress → view structured markdown output with headers, paragraphs, tables identified

### Tests for User Story 1

- [x] T025 [P] [US1] Contract test for POST /documents/upload and GET /documents/{id}/parse/progress (SSE) in `backend/tests/contract/test_documents_api.py`
- [x] T026 [P] [US1] Integration test for full parse pipeline (PDF → markdown) in `backend/tests/integration/test_parser_pipeline.py`

### Models for User Story 1

- [x] T027 [P] [US1] Create Document and ContentBlock SQLAlchemy models with DocumentStatus enum in `backend/src/models/document.py`
- [x] T028 [P] [US1] Create Alembic migration for documents, content_blocks tables: `backend/alembic/versions/002_documents.py`

### Services for User Story 1

- [x] T029 [US1] Implement HPD-Parsing wrapper: PyMuPDF render → dynamic tiling → model.generate_hpd() per HPD-PARSING-GUIDE in `backend/src/utils/hpd_parser.py`
- [x] T030 [US1] Implement parser service: orchestrate PDF upload → save to storage → queue Celery task → track progress in Redis in `backend/src/services/parser_service.py`
- [x] T031 [P] [US1] Implement Celery parse worker: load HPD model once, process pages sequentially, emit progress to Redis, handle CPU/GPU paths in `backend/src/workers/parse_worker.py`

### API for User Story 1

- [x] T032 [US1] Implement POST /documents/upload (multipart PDF, validate size/type, create Document, queue parse) in `backend/src/api/documents.py`
- [x] T033 [US1] Implement GET /documents/{id}/parse/progress (SSE endpoint: poll Redis job state, stream events) in `backend/src/api/documents.py`
- [x] T034 [US1] Implement GET /documents (paginated list, filter by status/language) and GET /documents/{id} (detail with blocks) in `backend/src/api/documents.py`
- [x] T035 [US1] Implement PATCH /documents/{id} (edit metadata, language, tags) and DELETE /documents/{id} (with SRS card warning) in `backend/src/api/documents.py`

### Frontend for User Story 1

- [x] T036 [P] [US1] Create DocumentUploader component with drag-and-drop, file size validation, language/dpi selectors in `frontend/src/components/document/DocumentUploader.tsx`
- [x] T037 [P] [US1] Create ParseProgress component with SSE listener, progress bar, page counter, ETA display in `frontend/src/components/document/ParseProgress.tsx`
- [x] T038 [US1] Create DocumentViewer page: rendered markdown with block types visually distinguished, page navigation in `frontend/src/app/documents/[id]/page.tsx`
- [x] T039 [US1] Create Documents list page with upload zone, status badges, language filters in `frontend/src/app/documents/page.tsx`

**Checkpoint**: User can upload a PDF, watch it parse, and view structured output. Deployable as MVP.

---

## Phase 4: User Story 2 — RAG Knowledge Base & Search (Priority: P1) 🎯 MVP

**Goal**: Parsed content is chunked, embedded, indexed in Qdrant. User can search across all documents with hybrid search.

**Independent Test**: Upload 3 PDFs → wait for indexing → search for a word → get ranked results from all 3 documents with context

### Tests for User Story 2

- [x] T040 [P] [US2] Contract test for GET /rag/search in `backend/tests/contract/test_rag_api.py`
- [x] T041 [P] [US2] Integration test for chunk → embed → index → search pipeline in `backend/tests/integration/test_rag_pipeline.py`

### Models & Schema for User Story 2

- [x] T042 [US2] Create KnowledgeSegment SQLAlchemy model in `backend/src/models/knowledge_segment.py`
- [x] T043 [US2] Create per-user Qdrant collection with dense (1024-dim) + sparse (BM25) vector config in `backend/src/core/qdrant.py`

### Services for User Story 2

- [x] T044 [P] [US2] Implement smart chunker: parse <BLOCK> tags, split by type (headers intact, tables intact, paragraphs at sentence boundaries, 200-500 tokens), 1-sentence overlap, min 50 tokens in `backend/src/utils/chunker.py`
- [x] T045 [US2] Implement embed service: load BGE-M3 model, batch encode chunks (32/batch), upsert to Qdrant with metadata payload in `backend/src/services/embed_service.py`
- [x] T046 [US2] Implement RAG service: hybrid search with RRF fusion (k=60), metadata filter pushdown (language, block_type, difficulty, document_id), highlight spans in `backend/src/services/rag_service.py`
- [x] T047 [US2] Implement Celery embed worker: trigger on parse completion, chunk → embed → index all pages in `backend/src/workers/embed_worker.py`

### API for User Story 2

- [x] T048 [US2] Implement GET /rag/search (query, language/type/difficulty filters, pagination) in `backend/src/api/rag.py`
- [x] T049 [US2] Implement GET /rag/chunks/{id} (single segment with surrounding context) and GET /rag/stats in `backend/src/api/rag.py`

### Frontend for User Story 2

- [x] T050 [P] [US2] Create SearchBar component with autocomplete, filter chips, results list with highlight spans in `frontend/src/components/document/SearchBar.tsx`
- [x] T051 [US2] Add search to document viewer and main navigation: search results overlay with source document/page links in `frontend/src/app/documents/[id]/page.tsx`

**Checkpoint**: User can search across all parsed documents with ranked, contextual results

---

## Phase 5: User Story 3 — Study Schedule & Daily Lessons (Priority: P1) 🎯 MVP

**Goal**: User creates a schedule → system auto-generates daily lessons with flashcards, reading, grammar, listening — all from RAG content

**Independent Test**: Create a schedule → system generates today's lesson with mixed content types → complete all items → see score

### Tests for User Story 3

- [x] T052 [P] [US3] Contract test for schedules and lessons endpoints in `backend/tests/contract/test_learning_api.py`
- [x] T053 [P] [US3] Integration test for schedule → lesson generation → item completion workflow in `backend/tests/integration/test_lesson_generation.py`

### Models for User Story 3

- [x] T054 [US3] Create Schedule and Lesson/LessonItem SQLAlchemy models in `backend/src/models/schedule.py`, `backend/src/models/learning.py`
- [x] T055 [US3] Create Alembic migration for schedules, lessons, lesson_items tables: `backend/alembic/versions/003_learning.py`

### Services for User Story 3

- [x] T056 [P] [US3] Implement schedule service: CRUD operations, validation (days 1-7, time, duration 5-120min, content_types subset, daily_item_count 5-50) in `backend/src/services/schedule_service.py`
- [x] T057 [US3] Implement LLM-powered content generation service: load Qwen3-0.6B (or similar lightweight model), extract flashcards (10-20/chapter), generate MCQs (3-5/passage: main idea, detail, inference, vocabulary), detect grammar patterns + generate fill-in-the-blank with distractors in `backend/src/services/generation_service.py`
- [x] T058 [US3] Implement lesson service: generate daily lesson from schedule + RAG content, interleave content types (40% vocab, 25% reading, 20% grammar, 15% listening), mix new + SRS review items, handle insufficient content edge case in `backend/src/services/lesson_service.py`
- [x] T059 [US3] Implement Celery lesson worker: nightly batch generation of tomorrow's lessons for all active schedules in `backend/src/workers/lesson_worker.py`

### API for User Story 3

- [x] T060 [US3] Implement POST/GET /schedules, PATCH/DELETE /schedules/{id} in `backend/src/api/learning.py`
- [x] T061 [US3] Implement GET /lessons/daily (auto-generate if not exists), POST /lessons/{id}/items/{item_id}/answer (evaluate response: case-insensitive, whitespace-normalized, fuzzy diacritics), POST /lessons/{id}/complete in `backend/src/api/learning.py`
- [x] T062 [US3] Implement GET /lessons/history (paginated, date range filter) in `backend/src/api/learning.py`

### Frontend for User Story 3

- [x] T063 [P] [US3] Create ScheduleBuilder component: day picker, time input, duration slider, content type checkboxes in `frontend/src/components/schedule/ScheduleBuilder.tsx`
- [x] T064 [P] [US3] Create Flashcard component: flip animation, term → definition + example, self-rate buttons (1-5), TTS play button in `frontend/src/components/learning/Flashcard.tsx`
- [x] T065 [P] [US3] Create ReadingPassage component: text display, MCQ questions with radio buttons, submit + feedback in `frontend/src/components/learning/ReadingPassage.tsx`
- [x] T066 [P] [US3] Create GrammarExercise component: fill-in-the-blank input, distractors shown as hint, submit + correct answer display in `frontend/src/components/learning/GrammarExercise.tsx`
- [x] T067 [US3] Create daily lesson page: fetch today's lesson, render items in interleaved order, track progress per item, submit all answers in `frontend/src/app/learning/page.tsx`
- [x] T067a [P] [US3] Create ListeningExercise component: TTS plays passage → user answers comprehension questions → auto-evaluate by keyword presence in `frontend/src/components/learning/ListeningExercise.tsx`

**Checkpoint**: Complete core learning loop — schedule → auto-generated lesson → study → score. This (US1+US2+US3) is the deployable MVP.

---

## Phase 6: User Story 7 — Offline-First Learning (Priority: P1) 🎯 MVP

**Goal**: Entire learning experience works offline. Documents, lessons, audio cached locally. Progress syncs automatically on reconnect.

**Independent Test**: Go offline → open app → complete a lesson → go online → verify progress synced to cloud

### Models for User Story 7

- [x] T068 [P] [US7] Create Device, SyncLog, and ProgressSnapshot SQLAlchemy models in `backend/src/models/device.py`, `backend/src/models/sync.py`, `backend/src/models/progress.py`
- [x] T069 [US7] Create Alembic migration for devices, sync_logs, progress_snapshots tables: `backend/alembic/versions/004_offline_sync.py`

### Backend for User Story 7

- [x] T070 [US7] Implement sync service: push (validate + merge LWW at item granularity, detect conflicts, return resolution), pull (query changes since timestamp) in `backend/src/services/sync_service.py`
- [x] T071 [US7] Implement POST /sync/push and GET /sync/pull endpoints in `backend/src/api/sync.py`
- [x] T072 [US7] Implement ProgressSnapshot daily aggregation (streak calculation, accuracy by type, study minutes) in `backend/src/services/progress_service.py`

### Frontend for User Story 7

- [x] T073 [P] [US7] Implement offline storage layer with IndexedDB (Dexie.js): cache documents, lessons, SRS cards, audio URLs in `frontend/src/lib/offline-db.ts`
- [x] T074 [US7] Implement offline sync hook: detect online/offline, queue changes when offline, execute push/pull on reconnect with exponential backoff retry in `frontend/src/hooks/useOffline.ts`
- [x] T075 [US7] Configure PWA: service worker with Workbox, offline fallback page, install prompt, app manifest in `frontend/src/app/manifest.ts`, `frontend/next.config.js`
- [x] T076 [US7] Add network status indicator and offline/online feature availability badges to UI in `frontend/src/components/ui/NetworkStatus.tsx`

**Checkpoint**: Full offline learning with automatic sync. Combined with US1–US3 = complete MVP.

---

## Phase 7: User Story 4 — TTS Voice & Audio System (Priority: P2)

**Goal**: Every content item has a play button. Audio generated via Edge TTS (online) or Piper TTS (offline), cached in Redis, with waveform visualization.

**Independent Test**: Click play on any flashcard/passage → hear audio within 2s (cached) → see waveform animation → switch voice/language/speed

### Tests for User Story 4

- [x] T077 [P] [US4] Contract test for TTS endpoints in `backend/tests/contract/test_tts_api.py`
- [x] T078 [P] [US4] Integration test for TTS pipeline (text → synthesize → cache → playback) in `backend/tests/integration/test_tts_pipeline.py`

### Services for User Story 4

- [x] T079 [P] [US4] Implement TTS service: Edge TTS primary, Piper TTS fallback, SHA-256 content hash for cache key, Redis audio cache with 30-day TTL + LRU eviction at 5GB/user, MP3 128kbps mono output in `backend/src/services/tts_service.py`
- [x] T080 [P] [US4] Implement audio cache utility: hash-based key generation, cache warming scheduler in `backend/src/utils/audio_cache.py`
- [x] T081 [US4] Implement Celery beat task for nightly TTS cache warming (next 2 days of lessons, 3am user-local time) in `backend/src/workers/lesson_worker.py`

### API for User Story 4

- [x] T082 [US4] Implement POST /tts/synthesize (text, language, voice, speed) and GET /tts/voices in `backend/src/api/tts.py`
- [x] T083 [US4] Implement GET /tts/audio/{hash} (stream cached audio file) in `backend/src/api/tts.py`

### Frontend for User Story 4

- [x] T084 [P] [US4] Create AudioPlayer component: play/pause, speed control (0.5x-2x), voice selector, download button in `frontend/src/components/tts/AudioPlayer.tsx`
- [x] T085 [P] [US4] Create Waveform visualization component using wavesurfer.js with `prefers-reduced-motion` fallback in `frontend/src/components/tts/Waveform.tsx`
- [x] T086 [US4] Integrate AudioPlayer into Flashcard, ReadingPassage, GrammarExercise, ListeningExercise components: add play button to every text content item

**Checkpoint**: All learning content is listenable with natural TTS in 8+ languages

---

## Phase 8: User Story 5 — Spaced Repetition System (Priority: P2)

**Goal**: Completed flashcards create SRS cards. Review cards appear in future lessons at expanding intervals based on SM-2 algorithm.

**Independent Test**: Complete 10 flashcards → review cards created → next day cards appear → rate each → intervals adjust

### Tests for User Story 5

- [x] T087 [P] [US5] Integration test for SRS workflow (lesson completion → card creation → review scheduling → interval progression) in `backend/tests/integration/test_srs_workflow.py`
- [x] T088 [P] [US5] Unit test for SM-2 algorithm correctness (all rating scenarios, EF bounds, leech detection, graduation) in `backend/tests/unit/test_srs_algorithm.py`

### Models & Services for User Story 5

- [x] T089 [US5] Create SRSCard SQLAlchemy model with SM-2 fields in `backend/src/models/srs.py`; Alembic migration: `backend/alembic/versions/005_srs.py`
- [x] T090 [US5] Implement SRS service: SM-2 algorithm (EF adjustments per rating, interval progression, leech detection at 5 consecutive 1s, graduation at first ≥3, minimum EF 1.3), due card query for lesson generation, card creation on flashcard completion in `backend/src/services/srs_service.py`

### Integration for User Story 5

- [x] T091 [US5] Integrate SRS card creation into POST /lessons/{id}/complete: create/update cards from completed flashcard items in `backend/src/api/learning.py`
- [x] T092 [US5] Integrate due review cards into GET /lessons/daily: query cards due today, interleave with new content in lesson generation in `backend/src/services/lesson_service.py`

**Checkpoint**: Vocabulary retention optimized through evidence-based spaced repetition

---

## Phase 9: User Story 6 — Progress Dashboard (Priority: P2)

**Goal**: Visual dashboard showing streaks (with calendar heatmap), vocabulary growth, study time charts, accuracy by content type.

**Independent Test**: Study for several days → open dashboard → see streak count, calendar, vocabulary chart, study time breakdown, accuracy chart

### Tests for User Story 6

- [x] T093 [P] [US6] Contract test for progress endpoints in `backend/tests/contract/test_progress_api.py`

### API for User Story 6

- [x] T094 [US6] Implement GET /progress/dashboard (current streak, total words, study minutes, daily snapshots for date range, accuracy by content type) in `backend/src/api/progress.py`
- [x] T095 [US6] Implement POST /progress/export-report (generate PDF report with all dashboard metrics) in `backend/src/api/progress.py`

### Frontend for User Story 6

- [x] T096 [P] [US6] Create StreakWidget with animated streak counter and calendar heatmap in `frontend/src/components/dashboard/StreakWidget.tsx`
- [x] T097 [P] [US6] Create VocabChart (line chart: words learned over time), StudyTimeChart (bar chart: minutes per day), AccuracyChart (radar/bar: accuracy by content type) in `frontend/src/components/dashboard/`
- [x] T098 [US6] Create progress dashboard page with all widgets, date range picker, export report button in `frontend/src/app/progress/page.tsx`

**Checkpoint**: Users can see their learning progress and stay motivated

---

## Phase 10: User Story 8 — Cross-Platform Mobile Apps (Priority: P2)

**Goal**: Native mobile apps for iOS and Android via React Native + Expo, sharing types and business logic with the web frontend.

**Independent Test**: Install from App Store / Google Play → log in → study on phone → switch to web → all progress synced

### Mobile App

- [x] T099 [P] [US8] Setup React Native navigation (stack + tabs), theme provider, API client with shared types in `mobile/src/navigation/`, `mobile/src/lib/`
- [x] T100 [P] [US8] Create mobile screens: Documents, Learning Session, Schedule, Dashboard, Settings — reusing shared types/constants, platform-adapted UI in `mobile/src/screens/`
- [x] T101 [US8] Implement mobile offline storage with WatermelonDB (SQLite): cache documents, lessons, SRS cards, audio in `mobile/src/lib/offline-db.ts`
- [x] T102 [US8] Configure Expo EAS Build for iOS and Android submission; configure push notifications (Expo Notifications) in `mobile/app.json`, `mobile/eas.json`
- [x] T103 [US8] Implement push notification handling: daily lesson reminder, sync completion in `mobile/src/lib/notifications.ts`

**Checkpoint**: Users can install native apps from app stores with full feature parity

---

## Phase 11: User Story 9 — Open Source & Community (Priority: P2)

**Goal**: GitHub repository is ready for public launch with docs, CI/CD, contribution guidelines, and self-hosting guide.

### Documentation & Repository

- [x] T104 [P] [US9] Create documentation site with VitePress: user guide, self-hosting guide, API reference, contributing guide in `docs/`
- [x] T105 [P] [US9] Create self-hosting deployment guide: Docker Compose production config, environment variables reference, hardware requirements (CPU minimum + GPU recommended), upgrade/migration guide in `docs/self-hosting/`
- [x] T106 [P] [US9] Create GitHub community files: ISSUE_TEMPLATE (bug, feature, question), PULL_REQUEST_TEMPLATE (constitution compliance checklist), SECURITY.md (vulnerability disclosure) in `.github/`
- [x] T107 [P] [US9] Create ROADMAP.md with public milestones: MVP, v1.0, community goals in `ROADMAP.md`
- [x] T108 [US9] Configure GitHub branch protection rules, CODEOWNERS file, and GitHub Discussions enabled in `.github/CODEOWNERS`

**Checkpoint**: Repository is public-ready — anyone can clone, self-host, and contribute

---

## Phase 12: User Story 10 — Authentication & User Management (Priority: P3)

**Goal**: Secure registration, login, email verification, OAuth, and data isolation.

**Independent Test**: Register → verify email → login → upload docs → logout → login → everything still there and private

### Tests for User Story 10

- [x] T109 [P] [US10] Contract test for auth endpoints in `backend/tests/contract/test_auth_api.py`

### Backend for User Story 10

- [x] T110 [US10] Build on T017: Implement POST /auth/register (email + password validation, verification email), POST /auth/login (JWT pair response), POST /auth/refresh, POST /auth/logout in `backend/src/api/auth.py`
- [x] T111 [US10] Implement POST /auth/oauth/{provider} (Google, GitHub callback), GET /auth/me, DELETE /auth/me (GDPR deletion with 30-day retention) in `backend/src/api/auth.py`
- [x] T112 [US10] Add user data isolation middleware: inject current user_id into all queries; validate document/schedule/lesson ownership on every request in `backend/src/core/dependencies.py`

### Frontend for User Story 10

- [x] T113 [P] [US10] Create login, register, OAuth callback pages with form validation and error display in `frontend/src/app/(auth)/`
- [x] T114 [US10] Create useAuth hook: token storage, refresh flow, redirect on expiry, user profile in `frontend/src/hooks/useAuth.ts`

**Checkpoint**: Secure multi-user system with data isolation

---

## Phase 13: User Story 11 — Community Support & Donations (Priority: P3)

**Goal**: Voluntary donation/support page linking to GitHub Sponsors and Ko-fi.

### Backend for User Story 11

- [x] T115 [US11] Create Donation SQLAlchemy model in `backend/src/models/donation.py`; Alembic migration: `backend/alembic/versions/006_donations.py`
- [x] T116 [US11] Implement GET /donations/support (platform links) and GET /donations (transparency list) in `backend/src/api/donations.py`

### Frontend for User Story 11

- [x] T117 [US11] Create donation/support page with GitHub Sponsors and Ko-fi links, community donor list (anonymous option respected), sustainability statement in `frontend/src/app/support/page.tsx`

### Team Features (P3 — per FR-033)

- [x] T117a [P] [US11] Create Team model and member invitation system (Team Admin sends invite, recipient accepts, shared library access) in `backend/src/models/team.py`; Alembic migration: `backend/alembic/versions/007_teams.py`
- [x] T117b [US11] Implement team management API: POST /teams, POST /teams/{id}/invite, GET /teams/{id}/members, shared document library endpoints in `backend/src/api/teams.py`
- [x] T117c [US11] Create team management page: invite members, view member list, shared document library, admin panel in `frontend/src/app/team/page.tsx`

**Checkpoint**: Community can support the project — all features remain 100% free. Team features available for collaborative learning.

---

## Phase 14: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [x] T118 [P] Implement virus scanning for uploaded PDFs: ClamAV async scan before parse queue in `backend/src/services/virus_scan_service.py`
- [x] T119 [P] Implement rate limiting: Redis token bucket, 100 req/min per user default, higher for SSE in `backend/src/core/rate_limit.py`
- [x] T120 [P] Implement CSP headers, CORS configuration, input sanitization for filenames/tags/search queries in `backend/src/core/security.py`
- [x] T121 [P] Implement GDPR data export endpoint: JSON export of all user data within 48 hours in `backend/src/api/auth.py`
- [x] T122 [P] Configure Sentry error tracking, Prometheus metrics export, Grafana dashboard template in `backend/src/core/monitoring.py`, `docker/prometheus.yml`
- [x] T122a [P] Implement public status page (health endpoint aggregation) and automated uptime monitoring with alerting (UptimeRobot or similar) to verify SC-016 (99.5% uptime SLA) in `docker/status-page/`
- [x] T123 [P] Add responsive design polish: test all pages at 375px, 768px, 1024px, 1440px; fix layout issues in `frontend/src/app/`
- [x] T124 [P] Add loading skeletons for all data-dependent views; add empty states (no documents, no lessons, no search results, zero streak) in `frontend/src/components/`
- [x] T125 [P] Add keyboard navigation and screen reader accessibility pass: focus trapping for modals, aria-labels, 44px touch targets in `frontend/src/components/`
- [x] T126 Run Lighthouse audit; achieve >90 Performance, Accessibility, Best Practices, SEO. Fix any violations.
- [x] T127 Run quickstart.md validation: verify all curl commands work end-to-end with seed data. Verify SC-001 through SC-016 measurable outcomes.
- [x] T128 Add end-to-end Playwright tests for critical user journeys: auth → upload → parse → search → schedule → study → dashboard in `frontend/tests/e2e/`
- [x] T129 [P] Update all dependency versions, run security audit, regenerate lockfiles in `backend/requirements.txt`, `frontend/package.json`, `mobile/package.json`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — can start after Phase 2
- **US2 (Phase 4)**: Depends on US1 (needs parsed content to index) + Foundational
- **US3 (Phase 5)**: Depends on US1 + US2 (needs parsed + indexed content for lesson generation)
- **US7 (Phase 6)**: Depends on US1 + US2 + US3 (needs working learning loop to make offline)
- **US4 (Phase 7)**: Depends on US3 (needs content items to attach audio to) — can start after Foundational if stubbed
- **US5 (Phase 8)**: Depends on US3 (needs flashcards to create SRS cards from)
- **US6 (Phase 9)**: Depends on US3 (needs learning data to visualize) + US7 (needs ProgressSnapshot)
- **US8 (Phase 10)**: Depends on US3 (needs working learning loop) — can start after Foundational with stubs
- **US9 (Phase 11)**: Depends on Phase 1 (needs repo setup) — can run in parallel with development
- **US10 (Phase 12)**: Depends on Foundational — can run early (auth needed for all stories)
- **US11 (Phase 13)**: No dependencies — runs independently
- **Polish (Phase 14)**: Depends on all user stories being complete

### User Story Dependency Graph

```
Phase 1: Setup
    ↓
Phase 2: Foundational
    ↓
    ├─→ US10 (Auth) ─────────────────────────────┐
    ├─→ US1 (Parse) ──→ US2 (RAG) ──→ US3 (Lessons) ──→ US5 (SRS)
    │                                      ↓              ↓
    │                                   US4 (TTS)    US6 (Dashboard)
    │                                      ↓              ↓
    │                                   US7 (Offline) ←──┘
    │                                      ↓
    ├─→ US8 (Mobile) ─────────────────────┘
    ├─→ US9 (Open Source) [parallel]
    └─→ US11 (Donations) [parallel]
         ↓
    Phase 14: Polish
```

### MVP Scope (Recommended First Delivery)

**US1 + US2 + US3 + US7 = Complete Learning MVP**

1. Phase 1: Setup
2. Phase 2: Foundational  
3. Phase 3: US1 — Upload & Parse
4. Phase 4: US2 — RAG Knowledge Base
5. Phase 5: US3 — Daily Lessons
6. Phase 6: US7 — Offline-First
7. **STOP & DEPLOY**: Working language learning app with document parsing, search, daily lessons, and offline support

---

## Parallel Opportunities

### Within Setup (Phase 1)
```bash
# Launch all [P] setup tasks together:
Task: "T002 Initialize backend Python project"
Task: "T003 Initialize frontend Next.js project"
Task: "T004 Initialize mobile React Native project"
Task: "T005 Initialize shared TypeScript package"
Task: "T006 Create Docker Compose dev stack"
Task: "T007 Configure GitHub Actions CI"
Task: "T008 Create README, LICENSE, CONTRIBUTING"
```

### Within Foundational (Phase 2)
```bash
# Backend foundation in parallel:
Task: "T012 Configure async SQLAlchemy"
Task: "T013 Configure Redis + Celery"
Task: "T014 Configure Qdrant client"
Task: "T015 Configure S3/MinIO storage"
Task: "T017 Implement JWT + OAuth2"
Task: "T018 Setup structured logging"

# Frontend foundation in parallel:
Task: "T020 Create API client"
Task: "T021 Create shared UI primitives"
Task: "T022 Implement theme toggle"
Task: "T023 Generate TypeScript types from OpenAPI"
Task: "T024 Define shared constants"
```

### Within User Stories
```bash
# US1 — Launch tests + models in parallel:
Task: "T025 Contract test for documents API"
Task: "T026 Integration test for parse pipeline"
Task: "T027 Create Document + ContentBlock models"
Task: "T028 Create Alembic migration"

# US3 — Launch all frontend components in parallel:
Task: "T063 Create ScheduleBuilder"
Task: "T064 Create Flashcard"
Task: "T065 Create ReadingPassage"
Task: "T066 Create GrammarExercise"
```

---

## Implementation Strategy

### MVP First (US1 + US2 + US3 + US7)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: US1 — Upload & Parse
4. Complete Phase 4: US2 — RAG Knowledge Base
5. Complete Phase 5: US3 — Daily Lessons
6. Complete Phase 6: US7 — Offline-First
7. **DEPLOY**: Working language learning app
8. Demo to users, gather feedback

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Demo (document parsing works!)
3. Add US2 → Test independently → Demo (search works!)
4. Add US3 → Test independently → **DEPLOY MVP** (learning loop complete!)
5. Add US7 → Test independently → Deploy (offline works!)
6. Add US4 → Deploy (TTS audio!)
7. Add US5 → Deploy (SRS retention!)
8. Add US6 → Deploy (progress tracking!)
9. Add US8 → Release mobile apps
10. Add US9 → Open source public launch
11. Add US10 + US11 → Multi-user + donations
12. Polish → Production hardening

### Parallel Team Strategy

With multiple developers after Foundational:
- Developer A: US1 → US2 → US3 (core pipeline)
- Developer B: US10 (auth) → US4 (TTS) → US5 (SRS)
- Developer C: US8 (mobile) → US6 (dashboard)
- Developer D: US9 (docs/community) + US11 (donations)

---

## Notes

- Total: **134 tasks** across 14 phases
- [P] tasks: can run in parallel (different files, no dependencies)
- [USx] label maps task to specific user story for traceability
- All file paths are relative to repository root
- Tests written FIRST, verified they FAIL, then implementation
- Each phase checkpoint validates the story independently before proceeding
- Commit after each task or logical group
