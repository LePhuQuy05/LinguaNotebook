# Quickstart: LinguaNotebook

**Phase 1 — Runnable validation guide for developers and contributors**

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11 or 3.12 | `python --version` |
| Node.js | 20 LTS or later | `node --version` |
| pnpm | 9.x | `pnpm --version` |
| Docker Desktop | 24+ | `docker --version` |
| Git | 2.40+ | `git --version` |
| GPU (optional) | 8GB+ VRAM for fast parsing | `nvidia-smi` or skipped for CPU |

---

## Quick Start (5 Minutes)

### 1. Clone and Configure

```bash
git clone https://github.com/your-org/lingua-notebook.git
cd lingua-notebook
cp .env.example .env
# Edit .env: set SECRET_KEY, optional STRIPE_API_KEY (skip for self-hosted)
```

### 2. Start the Full Stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

This starts:
- **postgres** — port 5432 (users, documents, learning data)
- **qdrant** — port 6333 (vector embeddings + hybrid search)
- **redis** — port 6379 (cache, Celery broker, sessions)
- **backend-api** — port 8000 (FastAPI with hot reload)
- **celery-worker** — (PDF parsing, embedding generation)
- **celery-beat** — (daily lesson generation, TTS cache warming)
- **frontend** — port 3000 (Next.js dev server with HMR)
- **minio** — port 9000 (S3-compatible local storage for PDFs/audio)

### 3. Run Database Migrations

```bash
docker compose exec backend-api alembic upgrade head
```

### 4. Verify Everything is Running

```bash
# API health check
curl http://localhost:8000/api/v1/health
# → {"status": "ok", "version": "1.0.0"}

# Readiness check (all dependencies)
curl http://localhost:8000/api/v1/health/ready
# → {"status": "ok", "postgres": "connected", "redis": "connected", "qdrant": "connected", "gpu_available": false}

# Frontend
open http://localhost:3000
```

---

## Development Workflow

### Backend (Python/FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest                          # All tests
pytest tests/unit               # Unit tests only
pytest tests/integration        # Integration tests
pytest tests/contract           # Contract tests

# Type check
mypy src/ --strict

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Run API locally (without Docker)
uvicorn src.main:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
pnpm install

# Run dev server
pnpm dev                        # http://localhost:3000

# Run tests
pnpm test                       # Jest unit + component tests
pnpm test:e2e                   # Playwright E2E tests

# Type check
pnpm typecheck

# Lint
pnpm lint

# Build
pnpm build
```

### Mobile (React Native + Expo)

```bash
cd mobile

# Install dependencies
pnpm install

# Start Expo dev server
npx expo start                  # Scan QR code with Expo Go

# Run on iOS simulator
npx expo run:ios

# Run on Android emulator
npx expo run:android

# Run tests
pnpm test

# Build for submission (EAS)
npx eas build --platform ios
npx eas build --platform android
```

### Shared Package

```bash
cd shared

pnpm install
pnpm build                      # Build TypeScript types
pnpm test
```

---

## Key Commands (via Makefile)

```bash
make dev          # Start all services via docker compose
make stop         # Stop all services
make test         # Run all tests (backend + frontend + mobile)
make lint         # Lint all codebases
make typecheck    # Type-check all codebases
make build        # Production build
make seed         # Seed database with demo data
make clean        # Remove build artifacts, reset Docker volumes
```

---

## Verification Scenarios

After setup, verify the core user journeys:

### VS1 — Upload & Parse a PDF

```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234","display_name":"Test User"}'

# 2. Login to get token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test1234"}' | jq -r '.access_token')

# 3. Upload a PDF
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf" \
  -F "language=en" \
  -F "dpi=100"

# → {"document_id": "...", "status": "parsing", "total_pages": null}

# 4. Watch parsing progress (SSE)
curl -N http://localhost:8000/api/v1/documents/{document_id}/parse/progress \
  -H "Authorization: Bearer $TOKEN"
# → data: {"status":"running","current_page":3,"total_pages":10,"elapsed_sec":45,...}
# → data: {"status":"completed","current_page":10,"total_pages":10}
```

### VS2 — Search Knowledge Base

```bash
# After VS1 completes, wait for indexing (~10-30s after parse completes)

curl "http://localhost:8000/api/v1/rag/search?q=vocabulary+word&language=en&limit=5" \
  -H "Authorization: Bearer $TOKEN"
# → {"results": [...ranked chunks with scores...], "took_ms": 45}
```

### VS3 — Create Schedule & Get Daily Lesson

```bash
# Create a schedule
curl -X POST http://localhost:8000/api/v1/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Evening Study",
    "days_of_week": [1,3,5],
    "time_of_day": "19:00",
    "duration_minutes": 30,
    "content_types": ["vocabulary","reading","listening"],
    "daily_item_count": 10
  }'

# Get today's lesson (auto-generated)
curl http://localhost:8000/api/v1/lessons/daily \
  -H "Authorization: Bearer $TOKEN"
# → {"id": "...", "status": "pending", "items": [...]}
```

### VS4 — Complete a Lesson & Sync Offline

```bash
# Submit answer for first item
ITEM_ID=$(curl -s http://localhost:8000/api/v1/lessons/daily \
  -H "Authorization: Bearer $TOKEN" | jq -r '.items[0].id')

curl -X POST "http://localhost:8000/api/v1/lessons/{lesson_id}/items/$ITEM_ID/answer" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"response":"correct answer","time_spent_seconds":15,"self_rating":4}'

# Complete the lesson
curl -X POST "http://localhost:8000/api/v1/lessons/{lesson_id}/complete" \
  -H "Authorization: Bearer $TOKEN"
# → {"score": 0.85, "words_learned": 8, "streak_days": 1}
```

### VS5 — TTS Audio Playback

```bash
# Generate audio
curl -X POST http://localhost:8000/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour le monde","language":"fr","voice":"default","speed":1.0}'
# → {"audio_url": "http://localhost:8000/api/v1/tts/audio/abc123", "duration_seconds": 2.1, "cached": false, "engine": "edge_tts"}

# Replay (cached)
curl -X POST http://localhost:8000/api/v1/tts/synthesize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text":"Bonjour le monde","language":"fr"}'
# → {"audio_url": "...", "cached": true, "engine": "edge_tts"}
```

---

## Self-Hosting Notes

For self-hosted deployment, see the full guide at `docs/self-hosting/`.

Key differences from cloud:
- Set `SELF_HOSTED=true` in `.env` — disables Stripe, enables all tiers for free
- CPU parsing is default (~2-3 min/page). GPU acceleration: set `GPU_ENABLED=true` and mount GPU in docker-compose.
- No external dependencies: MinIO replaces S3, Piper TTS handles all audio offline
- Single command: `docker compose -f docker/docker-compose.yml -f docker/docker-compose.selfhosted.yml up -d`

---

## Next Steps

- Run `/speckit-tasks` to generate the implementation task list
- Read the full [data model](./data-model.md) for entity details
- Read the [API contracts](./contracts/api.yaml) for all endpoints
- Read the [research decisions](./research.md) for technical rationale
