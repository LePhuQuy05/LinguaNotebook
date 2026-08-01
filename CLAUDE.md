# LinguaNotebook

Open-source (MIT) language learning web app. Upload PDFs → OCR → structured markdown → RAG knowledge base → personalized daily lessons.

## Stack

- **Backend**: Python 3.11+, FastAPI, Celery (Redis broker), SQLAlchemy 2.0 async
- **Frontend**: Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui
- **Infrastructure**: PostgreSQL, Qdrant (vector), Redis, MinIO (S3), Docker Compose
- **ML/OCR**: HPD-Parsing (PaddlePaddle, 1B params), Marker/surya VLM (evaluating)
- **GPU**: Intel Arc 140V (16GB), PyTorch XPU

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at repo root + `docs/adr/`. See `docs/agents/domain.md`.
