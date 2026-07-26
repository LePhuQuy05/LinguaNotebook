<!--
  Sync Impact Report
  ==================
  Version change: 1.0.0 → 2.0.0 (MAJOR)
  Reason: Backward-incompatible principle redefinition — Principle V changed from
          "Production-Ready & Monetizable" to "Production-Ready & Community-Sustained".
          Removed all payment/monetization language (Stripe, subscription tiers,
          feature gating). Application is now 100% free for all users.
  Modified principles:
    - V. Production-Ready & Monetizable → Production-Ready & Community-Sustained
      (removed Stripe, payment tiers, feature gating; added community sustainability)
    - VI. Code Quality & Testing (minor wording fix: removed "payments" from rationale)
  Added sections: None
  Removed sections: None
  Templates requiring updates:
    - .specify/templates/plan-template.md ✅ No changes needed (generic gate refs)
    - .specify/templates/spec-template.md ✅ No changes needed
    - .specify/templates/tasks-template.md ✅ No changes needed
    - specs/001-lingua-notebook/spec.md ⚠ Pending — needs premium tier removal
    - specs/001-lingua-notebook/plan.md ⚠ Pending — needs Stripe removal from tech context
  Follow-up TODOs:
    - Update spec to remove FR-016 (tiered accounts), FR-017 (self-hosted exemption),
      US11 (Premium Tiers), SC-010 (conversion rate), Subscription entity,
      contracts/payments.yaml
    - Update plan to remove Stripe from Technical Context, Stripe research decision (R7)
    - Update data-model.md to remove Subscription entity
-->

# LinguaNotebook Constitution

## Core Principles

### I. Document-First Learning (NON-NEGOTIABLE)

All learning content MUST originate from user-uploaded documents (PDFs, images).
HPD-Parsing (PaddlePaddle, 1B params) MUST parse every document into structured
markdown: headers, tables, text blocks, with bounding boxes. Parsed output MUST be
normalized and stored in a vector database for RAG retrieval.

**ABSOLUTELY NO hardcoded or canned learning content** — everything comes from user
documents. This principle ensures the learning experience is always personalized,
relevant, and driven by the user's own materials rather than generic curriculum.

### II. RAG-First Architecture (NON-NEGOTIABLE)

RAG (Retrieval-Augmented Generation) MUST be the central pathway for all knowledge
queries. Vector database (Qdrant) MUST store embeddings from all parsed content.
Hybrid search is MANDATORY: dense vector + sparse keyword (BM25) + metadata
filtering. RAG pipeline MUST support incremental index updates when users upload
new PDFs — no full re-indexing required.

No knowledge MUST ever be returned to the user without going through the RAG
pipeline. This ensures all responses are grounded in the user's actual documents
with full traceability to source material.

### III. Voice-First Interface

Every piece of learning content MUST be listenable via Text-to-Speech (TTS).
Multi-language support REQUIRED: English, Vietnamese, Chinese, Japanese, Korean,
French, German, Spanish (minimum 8 languages). Edge TTS serves as primary engine
(online, free, high quality); Piper TTS provides offline fallback.

Waveform visualization MUST render during audio playback. Users MUST be able to
select voice gender, speed, and language per content item. Audio caching is
MANDATORY to avoid redundant TTS generation for identical content.

### IV. Adaptive Learning Schedule

Users MUST be able to create fully customizable study schedules: time of day,
days of week, duration, content type preferences, and daily item count. The system
MUST auto-generate daily lessons from RAG content matched to each user's schedule.

Spaced Repetition System (SRS, SM-2 algorithm) MUST be integrated for optimal
long-term retention. Previously learned items MUST be automatically interleaved
with new content in each session. The dashboard MUST track: daily streaks,
vocabulary learned, total study time, and progress charts.

### V. Production-Ready & Community-Sustained

The system MUST be architected for production from day one: microservices
architecture (parsing service, RAG service, schedule service, API gateway) and
authentication & authorization (JWT + OAuth2 with Google and GitHub).

The application is **100% free for all users** — no paywalls, no premium tiers,
no feature gating. The cloud-hosted version and self-hosted version MUST offer
identical, complete feature sets. The project MUST be financially sustainable
through community donations, GitHub Sponsors, or other voluntary contribution
models, but MUST NEVER gate core features behind payment.

Infrastructure MUST include: rate limiting, structured logging, monitoring
(Prometheus + Grafana), error tracking (Sentry). Docker + Docker Compose for
development; Kubernetes-ready for production. CI/CD pipeline via GitHub Actions
(test → build → deploy).

### VI. Code Quality & Testing (NON-NEGOTIABLE)

Test-First Development: write tests BEFORE implementation — no exceptions. Test
suite MUST include: unit tests (pytest), integration tests, contract tests, and
E2E tests (Playwright). Type hints are MANDATORY for all Python code (mypy strict
mode). Minimum 80% code coverage enforced at CI gate.

Every API endpoint MUST have OpenAPI/Swagger documentation. Linting and
formatting: ruff, black (backend); prettier, eslint (frontend). All lint and type
checks MUST pass before merge. This principle exists because a language-learning
platform handling user documents requires zero tolerance for regressions.

### VII. Security & Privacy

All uploaded files MUST be virus-scanned before processing. Document content MUST
be encrypted at rest (AES-256). Strict user data isolation MUST be enforced:
each user sees ONLY their own data — no cross-user leakage through search, RAG,
or any other pathway.

GDPR-compliant data handling REQUIRED: data export endpoint, account deletion
with cascading data removal within 30 days. Input sanitization on every endpoint;
Content-Security-Policy headers; SQL injection prevention via ORM parameterization.
Authentication tokens MUST expire and be refreshable; passwords MUST be hashed
with bcrypt or argon2.

## Technical Constraints

The following technology choices are binding for this project:

- **Backend**: Python 3.11+, FastAPI, Celery (background tasks), SQLAlchemy 2.0 (ORM)
- **Frontend**: TypeScript 5.x, React 18+, Next.js 14 (App Router), Tailwind CSS, shadcn/ui
- **Relational Database**: PostgreSQL 15 (users, documents, schedules, learning data)
- **Vector Database**: Qdrant (embeddings, hybrid search)
- **Cache & Queue**: Redis (sessions, rate limiting, Celery broker, TTS audio cache)
- **ML / MLOps**: HPD-Parsing (PaddlePaddle, 1B params), BGE-M3 (multilingual embeddings),
  Piper TTS, Edge TTS
- **Infrastructure**: Docker Compose (local dev), GitHub Actions (CI/CD)
- **Deploy Targets**: Vercel (frontend), Railway or AWS ECS (backend services)
- **GPU Requirement**: Minimum 8 GB VRAM for HPD-Parsing (NVIDIA CUDA or Intel Arc XPU)

Deviation from any listed technology requires a documented amendment to this
constitution with rationale and migration assessment.

## Development Workflow & Quality Gates

1. **Branching**: Feature branches from `main`, named per spec-kit convention
2. **Pull Requests**: All changes require PR review. PR description MUST include
   a constitution compliance checklist.
3. **CI Gates** (must pass before merge):
   - Lint: ruff (backend), eslint + prettier (frontend)
   - Type check: mypy strict (backend), tsc (frontend)
   - Tests: pytest with coverage ≥80% (backend), Jest + Playwright (frontend)
   - Build: Docker images build successfully
4. **Spec-Kit Workflow**: Features flow through `/speckit-specify` → `/speckit-plan`
   → `/speckit-tasks` → `/speckit-implement`. No implementation may begin without
   an approved spec and plan.
5. **Complexity Justification**: Any architectural addition (new service, new
   database, new external dependency) MUST be recorded in the plan's Complexity
   Tracking table with a clear explanation of why a simpler alternative was rejected.

## Governance

This constitution is the supreme document of the LinguaNotebook project. It
supersedes all other practices, conventions, and ad-hoc decisions.

**Amendment Procedure**:
1. Propose amendment with rationale in a dedicated PR referencing this file
2. Document impact: which templates, services, and workflows are affected
3. Obtain explicit approval (the project owner)
4. Include a migration plan for any breaking governance changes
5. Update the Sync Impact Report at the top of this file

**Versioning Policy**: Semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Backward-incompatible governance/principle removals or redefinitions
- MINOR: New principle or section added, materially expanded guidance
- PATCH: Clarifications, wording, typo fixes, non-semantic refinements

**Compliance Review**: All pull requests MUST include a constitution compliance
checklist confirming alignment with each of the seven core principles. The
`/speckit-analyze` command may be used to cross-check artifacts against this
constitution.

**Complexity Justification**: Any deviation from the principle of simplicity
(e.g., adding a fourth database, introducing a new architectural pattern not
in the Technical Constraints) MUST be recorded in the plan.md Complexity
Tracking table with a clear explanation of why a simpler alternative was rejected.

**Version**: 2.0.0 | **Ratified**: 2026-07-25 | **Last Amended**: 2026-07-26
