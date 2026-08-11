# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# LinguaNotebook

Open-source (MIT) language learning web app: upload PDFs → OCR → structured markdown → RAG knowledge base → personalized daily lessons. Works fully offline, self-hostable.

## Layout

- `backend/` — Python 3.11–3.12, FastAPI, Celery, SQLAlchemy 2.0 async (`src/api`, `src/core`, `src/models`, `src/services`, `src/utils`, `src/workers`)
- `frontend/` — Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui
- `mobile/` — React Native + Expo; `shared/` — TS package with types for frontend/mobile
- `docker/docker-compose.yml` — PostgreSQL 15, Qdrant, Redis, MinIO, backend-api, celery-worker, celery-beat, frontend
- Specs/PRDs: `specs/001-lingua-notebook/` (spec.md, data-model.md, contracts/); research: `docs/research/`

## Commands

All services: `make dev` / `make stop` / `make seed` (wraps `docker compose -f docker/docker-compose.yml ...`). `make test`, `make lint`, `make typecheck`, `make build` run across backend + frontend + mobile.

Backend (from `backend/`, venv + `pip install -r requirements.txt`):
- Tests: `pytest` — **coverage ≥80% is enforced** (`--cov=src --cov-fail-under=80` in pyproject), so plain `pytest` fails on uncovered code. Single test: `pytest tests/unit/test_parse_worker.py::test_name`. Tests split into `tests/unit|integration|contract/`, fixtures in `tests/fixtures/`.
- Lint/format: `ruff check src/ tests/` / `ruff format src/ tests/` (line-length 100); typecheck: `mypy src/ --strict`
- Run API locally: `uvicorn src.main:app --reload --port 8000`
- Config is pydantic-settings from env with defaults pointing at localhost Docker services — `docker compose up` + `uvicorn` works without a `.env`

Frontend (from `frontend/`): `pnpm dev` (port 3000), `pnpm test` (jest, `--passWithNoTests`), `pnpm test:e2e` (Playwright), `pnpm typecheck`, `pnpm lint`, `pnpm build`.

Database: dev startup auto-creates tables (`src/main.py` lifespan) — Alembic (`backend/src/alembic/`) is for production migrations only: `docker compose exec backend-api alembic upgrade head`.

## Architecture: the parse pipeline (core flow)

```
POST /api/v1/documents/upload → PDF to MinIO → Celery parse_pdf task
→ parse_pdf_hybrid() auto-detects: text layer → PyMuPDF (instant);
  scanned → OCR_BACKEND setting: "paddle" → PaddleOCR-VL cloud API
  (services/paddle_ocr_service.py; no GPU needed) | "local" → HPD OCR
  (PaddlePaddle; GPU via PyTorch XPU on Intel Arc)
→ combined markdown with `--- Page N ---` page markers
→ upload parsed/<doc_id>/combined.md to MinIO
→ save typed ContentBlock rows (header/table/list/paragraph) to Postgres
```

- Progress streams via Redis keys `parse:progress:<doc_id>` (JSON: status/current_page/errors/...) and cancel flag `parse:cancel:<doc_id>`; the API polls these.
- The API still accepts a `mode` parameter but the **worker ignores it** (backward compat). Marker and hybrid (HPD + Qwen-VL re-parse) branches were removed after the 2026-08-01 parse proved hybrid was a silent no-op (spec 006). `services/qwen_vlm_parser.py` stays unwired for Stage 2. `parse_method` truthfully reports `text_layer` or `ocr`.
- `services/paddle_ocr_service.py` wraps the PaddleOCR-VL job API (submit → poll → JSONL): the bearer token lives in `PADDLE_OCR_TOKEN` (.env, gitignored) — never commit it. Each `layoutParsingResult` is one PDF page (one JSONL line can pack several); page numbers come from result order.
- `services/hpd_markdown.py` converts OCR markdown to typed blocks: conservative classifier (heading→paragraph degradation OK, table rows must never split). Page numbers come from the `--- Page N ---` markers, never array indexes.
- HPD degeneration fix: `_deduplicate_repeated_lines()` in `workers/parse_worker.py` collapses repeated lines before block parsing.
- `utils/hpd_parser.py` wraps the HPD engine itself; `services/pdf_parser.py` is the text-layer/OCR router.

## Celery workers (backend/src/workers/)

- `celery_app.py` routes by queue: parse_worker → `parsing`, embed_worker → `embedding`, lesson_worker → `lessons` (beat-scheduled: daily lesson generation, TTS cache warming).
- **Windows: `--pool=solo` is required** — prefork fails to deserialize tasks ("expected 3, got 0"). See `start_worker.bat`.
- **GPU worker runs on the host, not Docker** (Intel Arc 140V needs XPU passthrough): `python run_worker_gpu.py` — connects to Docker services on localhost, sets `GPU_ENABLED=true`, `GPU_TYPE=xpu`, `HPD_MODEL_PATH=backend/model`.
- Async gotcha: the worker keeps **one persistent asyncio loop** (`_get_event_loop()` in parse_worker.py). The asyncpg pool binds to the loop that created its connections; a loop created and closed per task crashes with "proactor.send on None" on Windows. Never close it.

## Data model (backend/src/models/)

`Document` → `ContentBlock` (page_number, `block_type` ∈ {header, table, list, paragraph}, content_markdown, bbox) + `KnowledgeSegment` (RAG chunks). Learning: `Schedule`, `Lesson`/`LessonItem`, `SRSCard` (SM-2). Offline sync: `Device`/`SyncLog`/`ProgressSnapshot`. JWT auth: 15-min access, 30-day refresh.

## Agent skills

- **Issue tracker**: issues are local markdown files at `.scratch/<feature-slug>/issues/NN-<slug>.md` — numbered from `01`, one file per ticket, never a combined file. Spec at `.scratch/<feature-slug>/spec.md`. Triage state in a `Status:` line near the top; conversation appends under `## Comments`. See `docs/agents/issue-tracker.md`.
- **Triage labels**: five canonical roles — `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.
- **Domain docs**: read `CONTEXT.md` at the repo root and `docs/adr/` if they exist — they don't yet, and per `docs/agents/domain.md` you should proceed silently and create them lazily rather than flagging their absence.

## Conventions & gotchas

- Frontend renders block content with react-markdown + remark-gfm (GFM tables) — do not revert to `dangerouslySetInnerHTML` for block content.
- MinIO stores PDFs + parsed markdown + TTS audio; Qdrant holds embeddings (hybrid semantic+keyword search via `services/rag_service.py`, `utils/chunker.py`).
- `make seed` seeds demo data (`backend/scripts/seed.py`).
