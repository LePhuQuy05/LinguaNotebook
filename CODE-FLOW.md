# 🦉 LinguaNotebook — Complete Code Flow & Architecture

> **Mục đích**: Hiểu sâu toàn bộ code, cách các file kết nối, luồng dữ liệu, và cách sửa lỗi.

---

## 1. TỔNG QUAN KIẾN TRÚC

```
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (:3000)                       │
│  Next.js 14 App Router + React + Tailwind + shadcn/ui    │
└────────────┬────────────────────────────────────────────┘
             │ HTTP (fetch / SSE)
             ▼
┌─────────────────────────────────────────────────────────┐
│                  FASTAPI (:8000)                         │
│  Python 3.11 + Uvicorn + SQLAlchemy 2.0 (async)         │
│                                                         │
│  src/main.py          ← Entry point, registers routes    │
│  src/api/*.py         ← Route handlers (8 modules)       │
│  src/services/*.py    ← Business logic (9 services)      │
│  src/models/*.py      ← ORM models (7 models)            │
│  src/core/*.py        ← Infrastructure (DB, Redis, etc)  │
│  src/workers/*.py     ← Celery background tasks          │
│  src/utils/*.py       ← HPD Parser wrapper, chunker      │
└──────┬──────┬─────────┬──────────┬──────────────────────┘
       │      │         │          │
       ▼      ▼         ▼          ▼
   ┌──────┐ ┌────┐ ┌───────┐ ┌─────────┐
   │Postgre│ │Redis│ │Qdrant │ │ MinIO   │
   │SQL 15│ │ 7  │ │Vector │ │ S3 API  │
   │:5432 │ │:6379│ │:6333  │ │ :9000   │
   └──────┘ └────┘ └───────┘ └─────────┘
```

**Tất cả chạy trong Docker Compose** — file `docker/docker-compose.yml`

---

## 2. CẤU TRÚC THƯ MỤC

```
D:\LanguageNotebook\
│
├── backend/                        ← PYTHON BACKEND
│   ├── Dockerfile                  ← Docker build (Python 3.11-slim)
│   ├── requirements.txt            ← Python dependencies
│   ├── pyproject.toml              ← Project config (ruff, mypy, pytest)
│   └── src/
│       ├── main.py                 ← ⭐ ENTRY POINT: FastAPI app
│       ├── api/                    ← Route handlers (HTTP endpoints)
│       │   ├── auth.py             ← POST /auth/register, /auth/login
│       │   ├── documents.py        ← POST /documents/upload, SSE progress
│       │   ├── learning.py         ← Schedules, daily lessons, answers
│       │   ├── rag.py              ← GET /rag/search (hybrid search)
│       │   ├── tts.py              ← POST /tts/synthesize
│       │   ├── sync.py             ← Offline sync push/pull
│       │   ├── progress.py         ← Dashboard, export report
│       │   └── donations.py        ← Support links
│       ├── services/               ← Business logic
│       │   ├── parser_service.py   ← Upload orchestration
│       │   ├── embed_service.py    ← BGE-M3 embeddings + Qdrant upsert
│       │   ├── rag_service.py      ← Hybrid search (RRF fusion)
│       │   ├── lesson_service.py   ← Daily lesson generation
│       │   ├── schedule_service.py ← Schedule CRUD
│       │   ├── tts_service.py      ← Edge TTS + Piper TTS
│       │   ├── srs_service.py      ← SM-2 spaced repetition
│       │   ├── sync_service.py     ← Offline sync with LWW
│       │   └── progress_service.py ← Dashboard aggregation (unused?)
│       ├── models/                 ← SQLAlchemy ORM models
│       │   ├── user.py             ← User table
│       │   ├── document.py         ← Document + ContentBlock tables
│       │   ├── knowledge_segment.py← KnowledgeSegment table
│       │   ├── schedule.py         ← Schedule table
│       │   ├── learning.py         ← Lesson + LessonItem tables
│       │   ├── srs.py              ← SRSCard table
│       │   └── sync.py             ← Device + SyncLog + ProgressSnapshot
│       ├── workers/                ← Celery background tasks
│       │   ├── celery_app.py       ← Celery instance + routing
│       │   ├── parse_worker.py     ← PDF parsing (HPD model)
│       │   ├── embed_worker.py     ← Chunking + embedding
│       │   └── lesson_worker.py    ← (empty — nightly lesson gen)
│       ├── core/                   ← Infrastructure
│       │   ├── config.py           ← Pydantic Settings (.env)
│       │   ├── database.py         ← Async SQLAlchemy engine + session
│       │   ├── redis.py            ← Redis client
│       │   ├── qdrant.py           ← Qdrant client + per-user collections
│       │   ├── storage.py          ← S3/MinIO file storage
│       │   ├── security.py         ← JWT tokens + bcrypt
│       │   ├── logging.py          ← Structlog
│       │   └── dependencies.py     ← FastAPI DI (auth, db)
│       ├── utils/
│       │   ├── hpd_parser.py       ← ⭐ HPD-Parsing wrapper (PDF→markdown)
│       │   └── chunker.py          ← Smart text chunking
│       └── tests/                  ← (empty — no tests written yet)
│
├── frontend/                       ← NEXT.JS WEB APP
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts          ← Design tokens as Tailwind theme
│   ├── tsconfig.json
│   ├── postcss.config.js
│   └── src/
│       ├── app/                    ← Next.js App Router pages
│       │   ├── layout.tsx          ← Root layout (fonts, Navbar, providers)
│       │   ├── page.tsx            ← Landing page ("LinguaNotebook")
│       │   ├── providers.tsx       ← Theme provider (dark/light)
│       │   ├── documents/
│       │   │   ├── page.tsx        ← Document list + upload
│       │   │   └── [id]/page.tsx   ← Document viewer
│       │   ├── learning/
│       │   │   └── page.tsx        ← Daily lesson (flashcards, reading, etc)
│       │   ├── schedule/
│       │   │   └── page.tsx        ← Schedule builder
│       │   └── progress/
│       │       └── page.tsx        ← Progress dashboard
│       ├── components/
│       │   ├── document/
│       │   │   ├── DocumentUploader.tsx  ← Drag-drop PDF upload
│       │   │   ├── ParseProgress.tsx     ← Real-time SSE progress bar
│       │   │   └── SearchBar.tsx         ← RAG search
│       │   ├── learning/
│       │   │   ├── Flashcard.tsx         ← Flip card + self-rating 1-5
│       │   │   ├── ReadingPassage.tsx    ← Text + answer input
│       │   │   ├── GrammarExercise.tsx   ← Fill-in-the-blank
│       │   │   └── ListeningExercise.tsx ← Play button + comprehension
│       │   ├── schedule/
│       │   │   └── ScheduleBuilder.tsx   ← Day picker, content types
│       │   ├── tts/                      ← (empty — TTS components)
│       │   ├── dashboard/                ← (empty — dashboard widgets)
│       │   └── ui/
│       │       ├── Navbar.tsx            ← Top navigation bar
│       │       └── NetworkStatus.tsx     ← Offline indicator
│       ├── hooks/
│       │   └── useOffline.ts             ← Online/offline detection + sync
│       ├── lib/
│       │   └── offline-db.ts             ← IndexedDB (Dexie.js)
│       └── styles/
│           ├── tokens.css                ← Design tokens (colors, fonts)
│           └── globals.css               ← Tailwind directives
│
├── mobile/                          ← REACT NATIVE (chưa chạy được)
├── shared/                          ← TypeScript types (chưa build)
├── docker/
│   └── docker-compose.yml           ← ⭐ 7 services
├── specs/001-lingua-notebook/       ← Tất cả tài liệu spec-kit
└── design-system/linguanotebook/    ← UI/UX design tokens
```

---

## 3. LUỒNG CHẠY CHI TIẾT

### 3.1. KHỞI ĐỘNG

```
1. docker compose -f docker/docker-compose.yml up -d

2. Docker builds backend image:
   Dockerfile → python:3.11-slim
   → apt-get install build-essential
   → pip install -r requirements.txt
   → COPY . /app

3. Container starts: uvicorn src.main:app --host 0.0.0.0 --port 8000

4. src/main.py executes:
   a. from src.core.config import settings     ← load .env
   b. from src.core.database import engine      ← create async engine
   c. app = FastAPI(...)                         ← create app
   d. Register ALL routers (8 modules):
      - auth.router       → /api/v1/auth/*
      - documents.router  → /api/v1/documents/*
      - learning.router   → /api/v1/schedules/*, /api/v1/lessons/*
      - rag.router        → /api/v1/rag/*
      - tts.router        → /api/v1/tts/*
      - sync.router       → /api/v1/sync/*
      - progress.router   → /api/v1/progress/*
      - donations.router  → /api/v1/donations/*
   e. Add CORS middleware
   f. Health endpoints: /api/v1/health, /api/v1/health/ready
```

### 3.2. USER REGISTERS / LOGS IN

```
BROWSER                          API                              DATABASE
───────                          ───                              ────────
POST /api/v1/auth/register  →   auth.py:register()               users table
{email, password, name}          │
                                 ├─ Check if email exists (SELECT)
                                 ├─ hash_password(password) → bcrypt
                                 ├─ User(email, hashed_pw, name)
                                 ├─ db.add(user)
                                 └─ db.commit()
                                 ← {id, email, "Account created"}

POST /api/v1/auth/login     →   auth.py:login()
{email, password}                │
                                 ├─ SELECT user by email
                                 ├─ verify_password(plain, hashed)
                                 ├─ create_access_token(user_id)  → JWT (15min TTL)
                                 ├─ create_refresh_token(user_id) → JWT (30 day TTL)
                                 └─ return {access_token, refresh_token, user}
```

**LƯU Ý QUAN TRỌNG**: Code hiện tại của `auth.py` dùng **Pydantic models** (RegisterRequest, LoginRequest) — đúng chuẩn FastAPI. Token được tạo bằng `jose.jwt` với algorithm HS256. KHÔNG dùng Query params cho password.

### 3.3. USER UPLOADS PDF — TOÀN BỘ PIPELINE

Đây là flow phức tạp nhất:

```
BROWSER                          API                              STORAGE/WORKER
───────                          ───                              ──────────────
1. User kéo PDF vào dropzone
   DocumentUploader.tsx
   → handleUpload(file)
   → FormData { file }
   → fetch POST /api/v1/documents/upload
      Header: Authorization: Bearer <token>

2.                                 documents.py:upload_document()
                                   │
                                   ├─ Validate: only .pdf, max 500MB
                                   ├─ Read file bytes: await file.read()
                                   ├─ parser_service.create_document()
                                   │  ├─ Upload file to MinIO:
                                   │  │  storage.upload_file(data, key, type)
                                   │  │  → MinIO bucket "linguanotebook"
                                   │  │  → key = "documents/{user_id}/{doc_id}/{filename}"
                                   │  ├─ Create Document record in DB
                                   │  │  status = "queued"
                                   │  └─ Dispatch Celery task:
                                   │     parse_pdf_task.delay(doc_id, key, dpi)
                                   │
                                   └─ Return {document_id, status, total_pages}

3.                                 parse_worker.py:parse_pdf_task()
   CELERY WORKER RUNS:            │
   ┌──────────────────────────────┤
   │  a. _get_parser()            │  ← Lazy-load HPD model (one-time)
   │     └─ HPDFParser(model_dir)  │
   │        ├─ load_model()        │
   │        │  ├─ AutoTokenizer.from_pretrained(model_dir,
   │        │  │     trust_remote_code=True, use_fast=False)
   │        │  └─ AutoModel.from_pretrained(model_dir,
   │        │       trust_remote_code=True, dtype=bfloat16,
   │        │       attn_implementation='eager')
   │        │  └─ model.load_mtp_weights()
   │        │
   │  b. Download PDF from MinIO   │
   │     → client.get_object(bucket, key)
   │     → pdf_bytes = response['Body'].read()
   │     → Write to temp file (PyMuPDF needs file path)
   │     │
   │  c. parser.parse_pdf(tmp_path, dpi=100)  │  ← Trang-by-trang
   │     │  FOR each page:          │
   │     │  ├─ PyMuPDF render → PIL Image (Zoom = dpi/72)
   │     │  ├─ Dynamic tiling: 448×448 tiles (max 24/page)
   │     │  ├─ model.generate_hpd() → structured markdown
   │     │  │    với <BLOCK> tags, bounding boxes
   │     │  ├─ Emit progress to Redis: parse:progress:{doc_id}
   │     │  └─ torch.cuda.empty_cache() mỗi 10 trang
   │     │
   │     └─ Return: combined markdown + errors list
   │
   │  d. Upload result markdown to MinIO
   │     → key = "parsed/{doc_id}/combined.md"
   │
   │  e. Signal completion in Redis
   │     → set_parse_progress(doc_id, {"status":"completed",...})
   │
   └──────────────────────────────┘

4. BROWSER: ParseProgress.tsx
   → EventSource(/api/v1/documents/{id}/parse/progress)
   → documents.py:parse_progress()
   → async generator: polls Redis every 1s
   → SSE stream: data: {current_page, total_pages, eta_sec, ...}
   → Khi status = "completed" → EventSource.close()
```

**BUG HIỆN TẠI TRONG PIPELINE NÀY**:
1. ❌ **HPD model chưa download** — Model `PaddlePaddle/HPD-Parsing` (~2GB) không có trong repo. Cần download từ HuggingFace vào `backend/model/`.
2. ❌ **Celery worker không chạy** — Docker Compose hiện chỉ start `backend-api`, không start `celery-worker` (nó có `profiles: [gpu]` nên cần `--profile gpu`).
3. ❌ **Sau khi parse xong, ContentBlock chưa được lưu vào DB** — `parse_worker.py` chỉ upload markdown lên MinIO, không parse markdown thành ContentBlock records và lưu vào PostgreSQL. Cần thêm bước này.
4. ❌ **Embed worker không được trigger** — Sau khi parse xong, cần gọi `embed_document_task.delay()` để chunk + embed + index.

### 3.4. RAG SEARCH

```
BROWSER                          API                              QDRANT
───────                          ───                              ──────
User gõ vào SearchBar       →   GET /api/v1/rag/search?q=...
                                   │
                                   rag.py:search()
                                   │
                                   rag_service.hybrid_search()
                                   │
                                   ├─ Generate query embeddings:
                                   │  ├─ BGE-M3 (dense, 1024-dim)
                                   │  └─ BM25 (sparse)
                                   │
                                   ├─ Dense search Qdrant:
                                   │  qdrant_client.search("user_{id}", dense_vector)
                                   │
                                   ├─ Sparse search Qdrant:
                                   │  qdrant_client.search("user_{id}", sparse_vector)
                                   │
                                   ├─ RRF Fusion (k=60):
                                   │  score = 1/(k+dense_rank) + 1/(k+sparse_rank)
                                   │
                                   └─ Return top-K results
```

**BUG**: Qdrant collection per-user cần được tạo trước khi search. `ensure_collection()` được gọi trong `embed_and_index_chunks()` nhưng nếu user chưa upload document nào thì collection chưa tồn tại → search sẽ lỗi.

### 3.5. DAILY LESSON

```
BROWSER                          API                              DATABASE / RAG
───────                          ───                              ──────────────
Vào /learning page           →   GET /api/v1/lessons/daily
                                   │
                                   learning.py:daily_lesson()
                                   │
                                   lesson_service.get_or_create_daily_lesson()
                                   │
                                   ├─ Check: có lesson cho hôm nay chưa?
                                   │  SELECT * FROM lessons
                                   │  WHERE user_id=X AND date=today
                                   │
                                   ├─ Nếu chưa có → generate_lesson():
                                   │  ├─ Tìm schedule active cho hôm nay
                                   │  ├─ Tính số lượng mỗi content type:
                                   │  │  40% vocab, 25% reading, 20% grammar, 15% listening
                                   │  ├─ Gọi RAG search để lấy content:
                                   │  │  hybrid_search(user_id, "key terms...", limit=N)
                                   │  ├─ Tạo LessonItem cho mỗi kết quả
                                   │  ├─ Gọi SRS service để lấy review cards
                                   │  ├─ Interleave (Fisher-Yates shuffle)
                                   │  └─ Save Lesson + LessonItems vào DB
                                   │
                                   └─ Return {lesson, items[]}

User trả lời flashcard       →   POST /lessons/{id}/items/{item_id}/answer
                                   │
                                   answer_item():
                                   ├─ Flashcard: self_rating 1-5 → is_correct = rating ≥ 3
                                   ├─ Typed answer: case-insensitive comparison
                                   └─ Listening: keyword overlap ≥ 50%

User complete lesson         →   POST /lessons/{id}/complete
                                   │
                                   complete_lesson():
                                   ├─ Tính score: correct / completed
                                   ├─ status → "completed"
                                   └─ Return {score, words_learned, streak_days}
```

### 3.6. OFFLINE SYNC

```
MOBILE/OFFLINE                   API                              DATABASE
─────────────                    ───                              ────────
User học offline:
  queueChange() → IndexedDB      (no internet)
  {entity_type, entity_id,
   action, payload, timestamp}

Khi online trở lại:
  useOffline.ts phát hiện
  "online" event
  → syncPendingChanges()
  → POST /api/v1/sync/push  →   sync.py:push()
  {device_id, changes[]}         │
                                 sync_service.push_changes()
                                 │
                                 ├─ For each change:
                                 │  ├─ Check conflict: entity có bị
                                 │  │  sửa bởi device khác không?
                                 │  ├─ Nếu có → LWW: server wins
                                 │  │  → return conflict
                                 │  └─ Nếu không → accept change
                                 │     → Save SyncLog
                                 │
                                 └─ Return {accepted, conflicts[]}

  → markSynced(ids)              ←
  → Xóa pending changes khỏi
    IndexedDB
```

---

## 4. DATABASE SCHEMA — TẤT CẢ CÁC BẢNG

```
users
├─ id (UUID PK)
├─ email (UNIQUE)
├─ hashed_password
├─ oauth_provider, oauth_id
├─ role (learner | team_admin | instance_admin)
├─ display_name, avatar_url
├─ is_email_verified, token_version
├─ created_at, updated_at, deleted_at

documents
├─ id (UUID PK)
├─ user_id (FK → users)
├─ filename, file_path (MinIO key), file_size_bytes, mime_type
├─ total_pages, dpi, language
├─ status (uploading|queued|parsing|completed|completed_with_errors|failed)
├─ error_message, parsed_content_path
├─ created_at, updated_at
└─ blocks → content_blocks (1:N)

content_blocks
├─ id (UUID PK)
├─ document_id (FK → documents)
├─ page_number, block_type (header|paragraph|table|list|image_caption)
├─ content_markdown (TEXT)
├─ bbox (JSON: [x1,y1,x2,y2])
├─ language, difficulty_level
└─ created_at

knowledge_segments
├─ id (UUID PK)
├─ user_id (FK → users)
├─ document_id (FK → documents)
├─ content (TEXT)
├─ source_block_ids (JSON: array of content_block IDs)
├─ block_type, chunk_index, token_count
├─ qdrant_point_id (UUID → Qdrant point)
├─ language, difficulty_level
├─ metadata_json (JSON)
└─ created_at

schedules
├─ id (UUID PK)
├─ user_id (FK → users)
├─ name, days_of_week (JSON: [1,3,5]), time_of_day
├─ duration_minutes, content_types (JSON), daily_item_count
├─ is_active
└─ created_at, updated_at

lessons
├─ id (UUID PK)
├─ user_id (FK → users)
├─ schedule_id (FK → schedules, nullable)
├─ date (DATE), status (pending|in_progress|completed)
├─ score (FLOAT), started_at, completed_at
├─ created_at
└─ items → lesson_items (1:N)

lesson_items
├─ id (UUID PK)
├─ lesson_id (FK → lessons)
├─ knowledge_segment_id (FK → knowledge_segments, nullable)
├─ item_type (flashcard|reading|grammar|listening)
├─ order_index, question, correct_answer
├─ user_response, is_correct, self_rating (1-5)
├─ time_spent_seconds, completed
└─ created_at

srs_cards
├─ id (UUID PK)
├─ user_id (FK → users)
├─ knowledge_segment_id (FK → knowledge_segments, nullable)
├─ front, back (TEXT)
├─ ease_factor, interval_days, repetitions
├─ next_review_date, last_review_date, last_score
├─ is_suspended, consecutive_failures
└─ created_at

devices
├─ id (UUID PK)
├─ user_id (FK → users)
├─ platform (web|ios|android)
├─ device_name, push_token, last_sync_at
└─ created_at

sync_logs
├─ id (UUID PK)
├─ user_id (FK → users), device_id (FK → devices)
├─ entity_type, entity_id, action (created|updated|deleted)
├─ synced_at, conflict_detected, conflict_resolution
└─ payload_hash

progress_snapshots
├─ id (UUID PK)
├─ user_id (FK → users)
├─ date (DATE)
├─ words_learned, words_reviewed, study_minutes, lessons_completed
├─ streak_days
├─ accuracy_vocabulary, accuracy_reading, accuracy_grammar, accuracy_listening
└─ created_at
```

---

## 5. CÁC FILE CONNECT VỚI NHAU NHƯ THẾ NÀO

```
main.py
├── imports config.py        ← settings (từ .env)
├── imports database.py      ← engine, AsyncSessionLocal, Base, get_db
├── imports logging.py       ← setup_logging()
├── imports dependencies.py  ← get_current_user_id (JWT validation)
│
├── app.include_router(auth.router)
│   └── auth.py
│       ├── imports security.py    ← hash_password, verify_password,
│       │                             create_access_token, decode_token
│       ├── imports database.py    ← get_db (DI)
│       ├── imports dependencies.py← get_current_user_id (DI)
│       └── imports models/user.py ← User model
│
├── app.include_router(documents.router)
│   └── documents.py
│       ├── imports parser_service.py  ← create_document, get_document, etc
│       │   └── imports storage.py     ← upload_file, get_file_url
│       │   └── imports redis.py       ← set_parse_progress
│       │   └── triggers: parse_worker.py  ← parse_pdf_task.delay()
│       │       └── imports hpd_parser.py  ← HPDFParser class
│       ├── imports models/document.py ← Document, ContentBlock, DocumentStatus
│       └── imports dependencies.py    ← get_current_user_id
│
├── app.include_router(rag.router)
│   └── rag.py
│       └── imports rag_service.py ← hybrid_search()
│           ├── imports embed_service.py ← generate_embeddings, generate_sparse_vectors
│           │   ├── SentenceTransformer("BAAI/bge-m3")
│           │   └── SparseTextEmbedding("Qdrant/bm25")
│           └── imports qdrant.py       ← qdrant_client, get_collection_name
│
├── app.include_router(learning.router)
│   └── learning.py
│       ├── imports schedule_service.py ← CRUD schedules
│       │   └── imports models/schedule.py
│       └── imports lesson_service.py   ← get_or_create_daily_lesson, answer, complete
│           ├── imports rag_service.py  ← hybrid_search (lấy content cho lesson)
│           └── imports srs_service.py  ← get_due_cards (review cards)
│               └── imports models/srs.py ← SRSCard model
│
├── app.include_router(tts.router)
│   └── tts.py
│       └── imports tts_service.py  ← synthesize()
│           ├── edge_tts (online primary)
│           └── piper_tts (offline fallback)
│
├── app.include_router(sync.router)
│   └── sync.py
│       └── imports sync_service.py ← push_changes, pull_changes
│           └── imports models/sync.py ← SyncLog, Device
│
├── app.include_router(progress.router)
│   └── progress.py
│       └── imports models/sync.py ← ProgressSnapshot
│
└── app.include_router(donations.router)
    └── donations.py
        └── imports config.py ← github_sponsors_url
```

---

## 6. CÁC BUG HIỆN TẠI & CÁCH SỬA

### BUG 1: Auth register/login bị lỗi khi dùng Query params
- **File**: `backend/src/api/auth.py` ✅ **ĐÃ SỬA** — Đã chuyển sang Pydantic request body
- **File**: `backend/Dockerfile` ⚠️ Cần thêm `bcrypt==4.0.1` vào requirements.txt

### BUG 2: `primary_key` → `primary_key=True`
- **Files**: Tất cả model files ✅ **ĐÃ SỬA** — Đã `sed -i 's/primary_key,/primary_key=True,/g'`

### BUG 3: `date` not imported in sync_service.py
- **File**: `backend/src/services/sync_service.py` ✅ **ĐÃ SỬA** — Đã thêm `date` vào import

### BUG 4: API routes không được register
- **File**: `backend/src/main.py` ✅ **ĐÃ SỬA** — Đã thêm `app.include_router()` cho tất cả 8 modules

### BUG 5: `@/styles/globals.css` không resolve được
- **Files**: Tất cả frontend files ✅ **ĐÃ SỬA** — Đã chuyển sang relative imports

### BUG 6: `@apply border-border` không tồn tại trong Tailwind
- **File**: `frontend/src/styles/globals.css` ✅ **ĐÃ SỬA** — Đã dùng CSS variables trực tiếp

### BUG 7: Celery worker không chạy
- **File**: `docker/docker-compose.yml` ✅ **ĐÃ SỬA** — Đã thêm `profiles: [gpu, all]`
- Chạy worker: `docker exec docker-backend-api-1 celery -A src.workers.celery_app worker --loglevel=info`

### BUG 8: Database tables không tự động tạo
- ✅ **ĐÃ SỬA** — `main.py` lifespan tự động gọi `Base.metadata.create_all()`

### BUG 9: HPD model chưa download
- **Folder**: `backend/model/` — trống
- **Cần**: Download từ HuggingFace `PaddlePaddle/HPD-Parsing` (~2GB)
- **Cách**: `cd backend && huggingface-cli download PaddlePaddle/HPD-Parsing --local-dir ./model`

### BUG 10: Parse worker không lưu ContentBlock vào DB
- **File**: `backend/src/workers/parse_worker.py` ✅ **ĐÃ SỬA**
- Đã thêm `_save_content_blocks()` — parse markdown → ContentBlock records → update Document status → trigger embed worker

### BUG 11: Frontend API calls không có base URL
- **File**: `frontend/next.config.js` ✅ **ĐÃ SỬA** — Đã thêm Next.js rewrites

### BUG 12: pnpm-lock.yaml không tồn tại
- **Issue**: CI yêu cầu lockfile
- **Fix**: Sau khi `pnpm install` thành công, commit `pnpm-lock.yaml`

### BUG 13: Không có trang đăng nhập (MỚI)
- ✅ **ĐÃ SỬA** — Login page `/login`, Register page `/register`, Navbar Sign in button

---

## 7. CÁCH CHẠY & DEBUG

### Start mọi thứ
```powershell
cd D:\LanguageNotebook

# Start databases + API
docker compose -f docker/docker-compose.yml up -d

# Start frontend (terminal riêng)
cd frontend
npx next dev -p 3000

# Xem logs API
docker logs -f docker-backend-api-1

# Vào container
docker exec -it docker-backend-api-1 bash
```

### Test API endpoints
```powershell
# Health
curl http://localhost:8000/api/v1/health

# List documents (cần token)
curl http://localhost:8000/api/v1/documents -H "Authorization: Bearer <token>"

# Search
curl "http://localhost:8000/api/v1/rag/search?q=test" -H "Authorization: Bearer <token>"
```

### Kiểm tra database
```powershell
docker exec -it docker-postgres-1 psql -U linguanotebook -d linguanotebook
# \dt              → list tables
# SELECT * FROM users;
# SELECT * FROM documents;
```

### Kiểm tra Qdrant
```powershell
curl http://localhost:6333/collections
```

---

## 8. THỨ TỰ SỬA ƯU TIÊN

| Priority | Bug | Status |
|----------|-----|--------|
| 🔴 P0 | #11 — API proxy | ✅ Fixed |
| 🔴 P0 | #13 — No login page | ✅ Fixed |
| 🔴 P0 | #10 — Lưu ContentBlock sau parse | ✅ Fixed |
| 🔴 P0 | #9 — Download HPD model | ⚠️ Cần user action |
| 🟡 P1 | #7 — Celery worker | ✅ Fixed (profiles) |
| 🟡 P1 | #8 — Auto-create tables | ✅ Fixed (lifespan) |
| 🟡 P1 | #1 — Auth bcrypt bug | ✅ Fixed |
| 🟡 P1 | #2 — primary_key bug | ✅ Fixed |
| 🟡 P1 | #3 — date import bug | ✅ Fixed |
| 🟡 P1 | #4 — API routes not registered | ✅ Fixed |
| 🟢 P2 | #12 — pnpm-lock.yaml | ⚠️ Cần user action |
| 🟢 P2 | Alembic migrations | Deferred |

---

## 9. CÁC FILE CHƯA ĐƯỢC DÙNG / CHƯA HOÀN THIỆN

| File | Status |
|------|--------|
| `backend/src/workers/lesson_worker.py` | Rỗng — chưa implement nightly lesson generation |
| `backend/src/services/progress_service.py` | Không được import ở đâu |
| `backend/src/api/sync.py` | Endpoint push chỉ return `{accepted:0, conflicts:[]}` — chưa implement |
| `backend/src/api/donations.py` | Return hardcoded data |
| `backend/tests/` | Trống — chưa có test nào |
| `frontend/src/lib/api.ts` | Không tồn tại — frontend dùng fetch trực tiếp |
| `frontend/src/components/tts/` | Thư mục trống |
| `frontend/src/components/dashboard/` | Thư mục trống |
| `mobile/` | Chưa chạy được (cần Expo setup) |
| `shared/` | Chưa build TypeScript |
