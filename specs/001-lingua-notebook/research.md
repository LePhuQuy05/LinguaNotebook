# Research: LinguaNotebook

**Phase 0 — Technical Research & Architecture Decisions**

---

## R1: HPD-Parsing Service Integration

**Decision**: Wrap HPD-Parsing in a dedicated Celery worker with GPU passthrough. CPU fallback as default for self-hosted. Model loaded once at worker startup, kept resident in VRAM (~2GB). Requests serialized through Celery queue (Redis broker).

**Rationale**:
- HPD-Parsing (PaddlePaddle/HPD-Parsing, 1B params) requires ~2GB VRAM in bf16 mode and ~15-30s per page. Cannot run per-request due to model load overhead.
- Celery worker pattern keeps the model hot in memory, processes jobs sequentially or with limited concurrency (1-2 concurrent parses depending on VRAM).
- CPU fallback via `model.to('cpu')` and `attn_implementation='eager'` makes self-hosting accessible. Performance degrades to ~2-3 min/page but is fully functional.
- PyMuPDF (fitz) renders PDF pages to PIL Image in-memory (no temp files). Dynamic tiling via `image_preprocess.py` splits into 448×448 tiles (max 24 per page).
- SSE progress streaming: the Celery task updates Redis with job state; the API endpoint polls Redis and pushes SSE events to the client.

**Alternatives Considered**:
- vLLM serving: Faster for batched inference but adds complexity and requires CUDA. Rejected for v1 — Celery pattern is simpler and works across CUDA/XPU/CPU.
- Direct inference in API process: Would block the event loop and leak VRAM. Rejected.
- gRPC worker: Better for multi-node but overkill for MVP. Can migrate later.

**References**: HPD-PARSING-GUIDE.md (C:\Users\ASUS\Downloads\HPD-Parsing\); HuggingFace model: `PaddlePaddle/HPD-Parsing`

---

## R2: Offline-First Sync Strategy

**Decision**: Last-write-wins (LWW) with timestamp resolution at the item level (LessonItem, SRSCard, ProgressSnapshot). Local SQLite (mobile) / IndexedDB (web) as offline store. Sync via REST API on reconnect — push local changes, pull remote changes, merge by max(timestamp).

**Rationale**:
- CRDTs provide perfect merge but add significant complexity (vector clocks, merge logic per entity). LWW is simpler and sufficient for a single-user-per-account learning app.
- Conflict probability is low: the user studies on one device at a time. Cross-device conflicts arise only if they study on phone and laptop while both offline, which is rare.
- Item-level granularity (not document-level) means studying flashcard #5 on phone and flashcard #6 on laptop doesn't create a conflict — both sync independently.
- For the rare true conflict (same card studied on two offline devices), LWW with user notification is acceptable per spec FR-024.
- Web: IndexedDB via Dexie.js. Mobile: WatermelonDB (SQLite) for React Native. Both provide observable queries matching the sync pattern.

**Alternatives Considered**:
- CRDT/Automerge: Gold standard for collaboration but over-engineered for single-user sync. Would triple the sync code complexity.
- Document-level sync: Simpler but causes false conflicts. Rejected — item-level granularity is worth the modest complexity increase.
- WebSockets real-time sync: Requires persistent connection, doesn't work offline. Rejected — async REST sync on reconnect is the right model.

---

## R3: Cross-Platform Code Sharing (Web + Mobile)

**Decision**: React Native + Expo for mobile apps. Shared TypeScript types, constants, and API client in a `shared/` package. UI components are platform-specific: shadcn/ui + Tailwind for web, React Native Paper or NativeBase for mobile.

**Rationale**:
- React Native + Expo is the fastest path to App Store + Google Play with a single codebase sharing ~70% of business logic. The spec already assumes "shared codebase for business logic."
- Expo provides OTA updates, push notifications, and EAS Build for CI — reducing mobile DevOps burden.
- shadcn/ui provides excellent web UX; React Native Paper provides Material Design native feel. Platform-appropriate UI is worth the component duplication for native feel (spec FR-020: "consistent UX adapted for device screen size and interaction patterns").
- Shared package includes: API types (generated from OpenAPI), validation schemas (Zod), auth token management, offline sync logic, SRS scheduling constants.

**Alternatives Considered**:
- Capacitor (web-in-native-shell): Simpler (one web codebase) but produces non-native-feeling apps. Rejected — spec explicitly calls for App Store + Google Play native apps, not just PWAs in a wrapper.
- Flutter: Excellent cross-platform but requires learning Dart and a separate ecosystem. Larger community contributor barrier for an open-source Python/TypeScript project.
- Kotlin Multiplatform + SwiftUI: Maximum native quality but two separate codebases. Rejected for v1 — would require 3x mobile engineering effort.

---

## R4: Qdrant Vector Database — Schema & Hybrid Search

**Decision**: Per-user collections in Qdrant for strong data isolation. Each collection uses: dense vectors (BGE-M3, 1024-dim) + sparse vectors (BM25 via fastembed) + payload fields for metadata filtering. Hybrid search with Reciprocal Rank Fusion (RRF).

**Rationale**:
- Per-user collections provide hardware-enforced data isolation (spec FR-032: "each user accesses only their own data"). No risk of cross-user leakage from a misconfigured query filter.
- Qdrant supports up to thousands of collections efficiently. At 1,000 users, 1,000 collections is well within Qdrant's design limits.
- BGE-M3 (BAAI/bge-m3) chosen for: multilingual support (100+ languages including Vietnamese, Chinese, Japanese, Korean), 1024-dim output, strong MTEB benchmarks, Apache 2.0 license compatible with open-source.
- BM25 sparse vectors via `fastembed` (Qdrant's embedding library) avoid external services. RRF fusion: `score = 1/(k + dense_rank) + 1/(k + sparse_rank)` with k=60.
- Metadata filter pushdown: `language`, `block_type`, `difficulty`, `document_id`, `user_id` filters applied before vector search for performance.

**Alternatives Considered**:
- Single collection with user_id filter: Simpler operations but security risk (one bad query leaks data). Rejected per constitution VII.
- Chroma: Simpler setup, good for prototypes, but lacks hybrid search and has weaker production scaling. Rejected — Qdrant's hybrid search is a hard requirement (spec FR-006).
- Pinecone/Weaviate: Managed services simplify ops but don't work for self-hosted open-source. Rejected — Qdrant supports both Docker self-hosting and Qdrant Cloud.
- Cohere Embed v3: Better multilingual quality than BGE-M3 in some benchmarks, but requires API key and doesn't work offline. Rejected — BGE-M3 can run locally, supporting self-hosted and offline scenarios.

---

## R5: TTS Pipeline Architecture

**Decision**: Two-tier TTS: Edge TTS (online, free, neural quality) as primary for 8+ languages, Piper TTS (offline, local ONNX models) as fallback. Redis audio cache with SHA-256 content hash as key, 30-day TTL. Cache warming for scheduled lessons.

**Rationale**:
- Edge TTS provides excellent quality across all 8 required languages at zero cost. No API key required. Latency: 1-3 seconds per request.
- Piper TTS runs locally via ONNX runtime. Voice models are 50-100MB per language/voice — downloaded on-demand and cached. Quality is lower than Edge TTS but fully functional offline (spec FR-011: "both online and offline playback capability").
- Audio caching: `tts:{engine}:{lang}:{voice}:{sha256(text)}` → WAV/MP3 bytes in Redis. Cache hit returns audio in <100ms. 30-day TTL prevents unbounded growth. Max 5GB per user.
- Cache warming: Celery beat task pre-generates TTS for tomorrow's lessons during off-peak (2-4 AM). Users wake up to instant audio.
- Frontend: wavesurfer.js (web) and expo-av (mobile) for waveform visualization and playback.

**Alternatives Considered**:
- Coqui AI / XTTS v2: Excellent quality, supports voice cloning, but requires GPU (2-4GB VRAM). Rejected — doesn't work on mobile or CPU-only self-hosted.
- Google Cloud TTS / AWS Polly: Production-grade but requires API keys, paid usage, and doesn't work offline. Rejected for open-source/self-hosted compatibility.
- Piper-only: Simpler architecture but lower quality than Edge TTS. The two-tier approach provides quality when online and functionality when offline.

---

## R6: SM-2 Spaced Repetition Algorithm

**Decision**: Standard SM-2 algorithm with language-learning-specific calibrations. Initial ease factor = 2.5. Rating scale: 1 (complete blackout), 2 (incorrect but recognized), 3 (correct with difficulty), 4 (correct with hesitation), 5 (perfect recall). Graduating interval = 1 day. Leeches detected after 5 consecutive scores of 1 and suspended.

**Rationale**:
- SM-2 is the most widely used SRS algorithm (Anki, Mnemosyne, etc.), well-understood by the language learning community, and simple to implement (~50 lines of code).
- Language-learning calibration from research (see `research/findings.md`): vocabulary benefits from slightly more aggressive intervals than general knowledge. Starting interval of 1 day (not 10 minutes) because users expect to review next day, not same day.
- Items graduate from "learning" to "review" after first score ≥3.
- Ease factor adjustments: score 5 → EF +0.1, score 4 → EF +0.0, score 3 → EF -0.14, score 2 → EF -0.22, score 1 → EF -0.30 (and reset to learning). Minimum EF = 1.3.
- Leech detection: cards repeatedly failed (score 1 five consecutive times) are suspended and flagged for user review ("This item may need a different approach").

**Alternatives Considered**:
- FSRS (Free Spaced Repetition Scheduler): Newer, ML-optimized algorithm used in Anki 23.10+. Better theoretical foundations but more complex to implement and harder to explain to users. Consider for v2.
- Leitner System: Simpler (5-box physical system) but less granular intervals. Rejected — SM-2 provides smoother interval progression.

---

## R7: Donation Integration (Amended per Constitution v2.0.0)

**Decision**: Voluntary donation support via GitHub Sponsors and Ko-fi. No payment tiers, no feature gating, no Stripe integration. A simple donation page links to external platforms. No `subscriptions` table — replaced by an optional `donations` table tracking voluntary contributions for community transparency only.

**Rationale**:
- Constitution v2.0.0 (2026-07-26): All features are 100% free. No paywalls, no premium tiers.
- GitHub Sponsors + Ko-fi handle payment processing externally — zero PCI scope for LinguaNotebook.
- A lightweight `donations` table (platform, amount optional, timestamp) exists solely for community transparency reporting (e.g., "This month's infrastructure costs: $X, community donations: $Y").
- Zero latency impact on requests — no tier lookup needed. All users have identical access.
- Self-hosted instances: donation page links to project's GitHub Sponsors (or can be disabled). No local donation tracking needed.

**Alternatives Considered**:
- Stripe Elements (custom UI): More design control but more PCI scope. Rejected for v1 — Checkout + Customer Portal is faster and safer.
- Stripe/Paddle/Lemon Squeezy: Previously considered for premium tiers (v1.0.0). Removed per constitution v2.0.0 — all features are free.
- Open Collective: Alternative to GitHub Sponsors for fiscal sponsorship. Consider if project grows to need a legal entity for donations.

---

## R8: Monorepo Tooling & CI/CD

**Decision**: Turborepo for monorepo orchestration. GitHub Actions for CI/CD. pnpm as package manager (strict, fast, disk-efficient). Backend managed separately via pip/requirements.txt (not part of the JS monorepo — coordinated via docker-compose).

**Rationale**:
- Turborepo handles task dependencies across `frontend/`, `mobile/`, and `shared/` packages: `turbo run build test lint --filter=...`. Caching avoids redundant work.
- pnpm chosen over npm/yarn for: strict dependency resolution (no phantom dependencies), disk efficiency (content-addressable store), and Turborepo first-class support.
- Python backend is not part of the JS build graph. A root `Makefile` coordinates: `make dev` (docker-compose up), `make test` (pytest + turbo test), `make build` (docker build + turbo build).
- CI pipeline: `.github/workflows/ci.yml` runs on every PR — lint (ruff + eslint + prettier), type-check (mypy + tsc), test (pytest + Jest), build (Docker + turbo build). All checks must pass before merge.
- Self-hosted users get the same pipeline via `docker compose -f docker/docker-compose.yml up`.

**Alternatives Considered**:
- Nx: More feature-rich but heavier and opinionated (Nx plugins for each framework). Turborepo is simpler and sufficient for a 3-package JS monorepo.
- Lerna: Legacy tool, largely superseded by Turborepo/Nx. Rejected.
- Rush: Microsoft's monorepo manager — excellent for massive repos (100+ packages) but overkill here. Rejected.
