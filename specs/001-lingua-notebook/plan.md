# Implementation Plan: LinguaNotebook

**Branch**: `001-lingua-notebook` | **Date**: 2026-07-25 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-lingua-notebook/spec.md`

## Summary

LinguaNotebook is a cross-platform, open-source language learning application that parses user-uploaded PDF documents into structured, searchable content using HPD-Parsing, indexes it into a RAG-powered knowledge base, and generates personalized daily lessons with spaced repetition and multilingual text-to-speech. The system supports web (Next.js), iOS, and Android (shared React Native codebase), operates fully offline with automatic cloud sync, and offers a cloud-hosted tiered service (Free/Pro/Team) alongside a fully-featured self-hosted open-source deployment path.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.x (frontend/mobile/shared)

**Primary Dependencies**: FastAPI (API), Celery (background tasks), Next.js 14 App Router (web), React Native + Expo (mobile), SQLAlchemy 2.0 (ORM), PyMuPDF (PDF rendering), HuggingFace Transformers 4.x (HPD-Parsing), sentence-transformers (BGE-M3 embeddings), Qdrant (vector DB), Redis (cache/queue/broker), edge-tts + piper-tts (TTS), Tailwind CSS + shadcn/ui (styling)

**Storage**: PostgreSQL 15 (users, documents, schedules, learning data, donations), Qdrant (embeddings + hybrid search), Redis (sessions, Celery broker, TTS audio cache, rate limiting), S3-compatible object storage — MinIO for self-hosted / Cloudflare R2 or S3 for cloud (PDFs, parsed markdown, audio files)

**Testing**: pytest + pytest-asyncio + httpx (backend), Jest + React Testing Library (frontend), Playwright (E2E), Detox or Maestro (mobile E2E)

**Target Platform**: Web (modern browsers, mobile-responsive, PWA), iOS 16+ (iPhone + iPad via App Store), Android 13+ (phones + tablets via Google Play), Docker (self-hosted, Linux server)

**Project Type**: Web application + Mobile apps — monorepo with shared business logic

**Performance Goals**: PDF parsing <5min/100pg (GPU) or ~3min/pg (CPU self-hosted), RAG search <1s for 10K chunks, TTS playback <2s cached / <5s new, web TTI <3s desktop / <5s mobile, mobile cold launch <3s, 1000 concurrent cloud users without degradation

**Constraints**: CPU-only parsing fully supported for self-hosted (slower but functional), offline-first (all learning features work without internet), PWA with service worker caching, 99.5% cloud uptime with <1h RTO, 80% code coverage minimum, MIT license

**Scale/Scope**: 1,000 concurrent cloud users, 10K+ knowledge segments per user, 8+ TTS languages, 3 platforms (web + iOS + Android), 36 functional requirements, 16 success criteria

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| I. Document-First Learning | ✅ PASS | All content sourced from user-uploaded PDFs; no canned content (spec FR-002, FR-003, US1) |
| II. RAG-First Architecture | ✅ PASS | RAG is central query pathway; hybrid search required; incremental indexing (spec FR-005–FR-007, US2) |
| III. Voice-First Interface | ✅ PASS | TTS on every content item; 8+ languages; online + offline; waveform visualization (spec FR-011–FR-013, US4) |
| IV. Adaptive Learning Schedule | ✅ PASS | Customizable schedules; auto-generated daily lessons; SRS integrated; dashboard tracking (spec FR-008–FR-010, US3, US5, US6) |
| V. Production-Ready & Community-Sustained | ✅ PASS | Microservices architecture; JWT + OAuth2; 100% free for all users; Docker + CI/CD; Prometheus + Grafana; community donations for sustainability (spec FR-016, FR-017, US11, SC-007, SC-016) |
| VI. Code Quality & Testing | ✅ PASS | Test-first; pytest + Jest + Playwright; mypy strict; 80% coverage; OpenAPI docs (constitution VI) |
| VII. Security & Privacy | ✅ PASS | Data isolation (FR-032); encrypted storage; GDPR deletion within 30 days (US10); input sanitization; CSP headers |

**Gate Result**: ALL PASS — No violations. Proceed to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/001-lingua-notebook/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (OpenAPI specs)
│   ├── auth.yaml
│   ├── documents.yaml
│   ├── learning.yaml
│   ├── rag.yaml
│   ├── tts.yaml
│   ├── progress.yaml
│   └── payments.yaml
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
lingua-notebook/
├── backend/                       # Python FastAPI + Celery
│   ├── src/
│   │   ├── api/                   # Route handlers
│   │   │   ├── auth.py            # POST /auth/register, /auth/login, /auth/refresh
│   │   │   ├── documents.py       # POST /documents/upload, GET /documents/{id}/parse/progress (SSE)
│   │   │   ├── learning.py        # POST /schedules, GET /lessons/daily, POST /lessons/{id}/complete
│   │   │   ├── rag.py             # GET /rag/search, GET /rag/chunks/{id}
│   │   │   ├── tts.py             # POST /tts/synthesize, GET /tts/voices, GET /tts/audio/{hash}
│   │   │   ├── progress.py        # GET /progress/dashboard, GET /progress/export-report
│   │   │   └── payments.py        # POST /payments/create-checkout, POST /payments/webhook
│   │   ├── models/                # SQLAlchemy ORM models
│   │   │   ├── user.py            # User, UserRole enum
│   │   │   ├── document.py        # Document, DocumentStatus enum, ParsedBlock, BlockType enum
│   │   │   ├── schedule.py        # Schedule, ContentType enum
│   │   │   ├── learning.py        # Lesson, LessonStatus enum, LessonItem, ItemType enum
│   │   │   ├── srs.py             # SRSCard
│   │   │   ├── progress.py        # ProgressSnapshot
│   │   │   └── payment.py         # Subscription, PlanTier enum
│   │   ├── services/              # Business logic
│   │   │   ├── parser_service.py  # HPD-Parsing: PyMuPDF → HPD → structured markdown
│   │   │   ├── chunker_service.py # Block-type-aware chunking
│   │   │   ├── embed_service.py   # BGE-M3 embeddings + Qdrant upsert
│   │   │   ├── rag_service.py     # Hybrid search: dense + sparse + metadata
│   │   │   ├── schedule_service.py
│   │   │   ├── lesson_service.py  # Lesson generation engine
│   │   │   ├── tts_service.py     # Edge TTS + Piper TTS + Redis cache
│   │   │   ├── srs_service.py     # SM-2 algorithm
│   │   │   ├── sync_service.py    # Offline sync + conflict resolution
│   │   │   ├── payment_service.py # Stripe checkout + webhooks
│   │   │   └── progress_service.py
│   │   ├── workers/               # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── parse_worker.py    # GPU/CPU PDF parsing
│   │   │   ├── embed_worker.py    # Chunk + embed + index
│   │   │   └── lesson_worker.py   # Nightly lesson generation batch
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic settings
│   │   │   ├── security.py        # JWT + OAuth2 + password hashing
│   │   │   ├── database.py        # AsyncSession + engine
│   │   │   ├── storage.py         # S3/MinIO abstraction
│   │   │   └── dependencies.py    # FastAPI DI
│   │   └── utils/
│   │       ├── hpd_parser.py      # HPD-Parsing wrapper (per HPD-PARSING-GUIDE)
│   │       ├── chunker.py         # Smart chunking by block type
│   │       └── audio_cache.py     # Redis audio cache (hash-based keys)
│   ├── alembic/
│   ├── tests/
│   │   ├── contract/              # API contract tests
│   │   ├── integration/           # Service pipeline tests
│   │   └── unit/                  # Unit tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/                      # Next.js 14 web app
│   ├── src/
│   │   ├── app/                   # App Router pages
│   │   ├── components/            # UI components
│   │   │   ├── ui/                # shadcn/ui primitives
│   │   │   ├── document/          # Uploader, Viewer, Editor, ParseProgress
│   │   │   ├── learning/          # Flashcard, ReadingPassage, GrammarExercise, ListeningExercise
│   │   │   ├── tts/               # AudioPlayer, Waveform
│   │   │   ├── schedule/          # ScheduleBuilder, WeeklyCalendar
│   │   │   └── dashboard/         # StreakWidget, Charts
│   │   ├── hooks/                 # useSSE, useTTS, useAuth, useRAG, useOffline
│   │   ├── lib/                   # API client, auth, offline sync
│   │   └── styles/
│   ├── public/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
│
├── mobile/                        # React Native + Expo
│   ├── src/
│   │   ├── screens/               # Equivalent pages to web app
│   │   ├── components/            # Native UI adaptations
│   │   ├── hooks/                 # Shared hooks + native-specific
│   │   └── lib/                   # API client, offline storage (SQLite/WatermelonDB)
│   ├── ios/
│   ├── android/
│   ├── tests/
│   ├── app.json                   # Expo config
│   └── package.json
│
├── shared/                        # Shared across frontend + mobile
│   ├── src/
│   │   ├── types/                 # TypeScript types matching backend schemas
│   │   ├── constants/             # Shared constants (languages, tiers, limits)
│   │   └── utils/                 # Validation, date formatting, etc.
│   └── package.json
│
├── docker/                        # Infrastructure configs
│   ├── docker-compose.yml         # Full dev stack
│   ├── docker-compose.prod.yml    # Production override
│   ├── nginx.conf                 # Reverse proxy
│   └── prometheus.yml             # Monitoring config
│
├── docs/                          # Documentation site (VitePress or Docusaurus)
│   ├── index.md                   # Landing page
│   ├── guide/                     # User guide
│   ├── self-hosting/              # Self-hosting deployment guide
│   └── contributing/              # CONTRIBUTING guide
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                 # Lint, type-check, test on PR
│   │   ├── deploy-cloud.yml       # Deploy cloud version
│   │   └── deploy-docs.yml        # Deploy docs site
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── LICENSE                         # MIT or Apache 2.0
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── ROADMAP.md
├── Makefile                        # Common commands
├── .env.example
├── design-system/                   # UI/UX design system (ui-ux-pro-max)
│   └── linguanotebook/
│       ├── MASTER.md               # Global design authority
│       ├── tokens.css              # Three-layer CSS tokens (primitive→semantic→component)
│       ├── tailwind.config.ts      # Tailwind configuration
│       └── pages/                  # Per-page design overrides
│
└── turbo.json                      # Turborepo config
```

**Structure Decision**: Monorepo with Turborepo orchestration. The `shared/` package contains TypeScript types, constants, and utilities consumed by both `frontend/` (Next.js web) and `mobile/` (React Native + Expo). Backend is a separate Python project with its own dependency management. This avoids the "Option 3 (Mobile + API)" pattern where mobile is completely separate — instead, the frontend web PWA already handles mobile web, and React Native shares types and business logic for native app store distribution.

## Complexity Tracking

> No constitutional violations. No complexity justifications required.
