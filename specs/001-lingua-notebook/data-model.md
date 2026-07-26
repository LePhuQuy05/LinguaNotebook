# Data Model: LinguaNotebook

**Phase 1 — Entity definitions, relationships, state machines, and validation rules**

---

## Entity-Relationship Overview

```
User ──< Document ──< ContentBlock ──< KnowledgeSegment
User ──< Schedule ──< Lesson ──< LessonItem
User ──< SRSCard
User ──< ProgressSnapshot
User ──< Device
User ──< Donation (optional, cloud only)
User ──< SyncLog
```

---

## Entities

### User

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK, default uuid4 | Unique identifier |
| email | String(255) | UNIQUE, NOT NULL, indexed | Login email |
| hashed_password | String(255) | NOT NULL (nullable if OAuth only) | bcrypt hash |
| oauth_provider | String(50) | NULLABLE, enum: google, github | External auth provider |
| oauth_id | String(255) | NULLABLE | External provider user ID |
| role | Enum | NOT NULL, default: learner | learner, team_admin, instance_admin |
| display_name | String(100) | NOT NULL | Visible name |
| avatar_url | String(500) | NULLABLE | Profile picture URL |
| is_email_verified | Boolean | NOT NULL, default: false | Email confirmation status |
| created_at | DateTime | NOT NULL, default: now | Account creation timestamp |
| updated_at | DateTime | NOT NULL, onupdate: now | Last modification |
| deleted_at | DateTime | NULLABLE | Soft-delete for GDPR (30-day retention) |

**Validation**:
- email: valid email format, max 255 chars
- password: min 8 chars, at least 1 letter + 1 number (enforced at registration)
- role: instance_admin only valid when `SELF_HOSTED=true`
- Exactly one auth method required: (email + password) OR (oauth_provider + oauth_id)

**Relationships**:
- Has many: Document, Schedule, Lesson, SRSCard, ProgressSnapshot, Device, SyncLog
- Has many: Donation (cloud only, optional)

---

### Device

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| platform | Enum | NOT NULL | web, ios, android |
| device_name | String(200) | NOT NULL | Human-readable: "iPhone 16 Pro" |
| push_token | String(500) | NULLABLE | FCM/APNs token |
| last_sync_at | DateTime | NULLABLE | Last successful sync |
| offline_data_path | String(500) | NULLABLE | Local storage identifier |
| created_at | DateTime | NOT NULL | First registration |

**Uniqueness**: (user_id, platform, device_name) unique constraint

---

### Document

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| filename | String(500) | NOT NULL | Original filename |
| file_path | String(1000) | NOT NULL | S3/MinIO object key |
| file_size_bytes | BigInteger | NOT NULL | Size in bytes |
| mime_type | String(100) | NOT NULL | application/pdf |
| total_pages | Integer | NULLABLE | Set after parsing |
| dpi | Integer | NOT NULL, default: 100 | Rendering DPI |
| language | String(10) | NULLABLE | ISO 639-1 code (detected after parse) |
| status | Enum | NOT NULL, default: uploading | See state machine |
| error_message | Text | NULLABLE | Last error if failed |
| parsed_content_path | String(1000) | NULLABLE | S3/MinIO key for combined markdown |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

**Validation**:
- file_size_bytes: max 524,288,000 (500MB)
- mime_type: must be application/pdf
- dpi: 72, 100, 150, or 200
- language: valid ISO 639-1 or NULL

**State Machine — DocumentStatus**:
```
uploading → queued → parsing → completed
                        ↓         ↓
                      failed ←───┘
                        
uploading → failed (upload interrupted)
parsing → completed_with_errors (some pages failed, result still usable)
```

---

### ContentBlock

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| document_id | UUID | FK → Document, NOT NULL, indexed | Source document |
| page_number | Integer | NOT NULL | 1-indexed page |
| block_type | Enum | NOT NULL | header, paragraph, table, list, image_caption |
| content_markdown | Text | NOT NULL | Parsed markdown content |
| bbox | JSON | NULLABLE | [x1, y1, x2, y2] bounding box |
| language | String(10) | NOT NULL | ISO 639-1 |
| difficulty_level | Enum | NULLABLE, default: intermediate | beginner, intermediate, advanced |
| created_at | DateTime | NOT NULL |

**Validation**:
- page_number: ≥ 1
- content_markdown: not empty
- bbox: array of 4 integers, or null

**Relationship**: Belongs to Document. Feeds into KnowledgeSegment (one or more blocks → one segment).

---

### KnowledgeSegment

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner (denormalized for RAG queries) |
| document_id | UUID | FK → Document, NOT NULL | Source document |
| content | Text | NOT NULL | Combined text of constituent blocks |
| source_block_ids | JSON | NOT NULL | Array of ContentBlock UUIDs |
| block_type | Enum | NOT NULL | Dominant block type |
| chunk_index | Integer | NOT NULL | Position in document |
| token_count | Integer | NOT NULL | Approximate token count |
| qdrant_point_id | UUID | NOT NULL, indexed | Qdrant point reference |
| language | String(10) | NOT NULL | ISO 639-1 |
| difficulty_level | Enum | NOT NULL | beginner, intermediate, advanced |
| metadata_json | JSON | NOT NULL | All searchable metadata |
| created_at | DateTime | NOT NULL |

**Validation**:
- chunk_index: ≥ 0, unique per document
- token_count: > 0
- metadata_json: must include language, block_type, difficulty, document_id, page_number_range

**Qdrant Collection Schema** (per user):
- vectors.dense: 1024-dim float (BGE-M3)
- vectors.sparse: BM25 sparse vector (fastembed)
- payload: {user_id, document_id, block_type, language, difficulty, page_start, page_end, chunk_index, token_count, created_at}

---

### Schedule

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| name | String(200) | NOT NULL | "French Evening Study" |
| days_of_week | JSON | NOT NULL | [1,3,5] (Mon=1, Sun=7) |
| time_of_day | Time | NOT NULL | 19:00 |
| duration_minutes | Integer | NOT NULL | 30 |
| content_types | JSON | NOT NULL | ["vocabulary","reading","grammar","listening"] |
| daily_item_count | Integer | NOT NULL, default: 10 | New items per session |
| is_active | Boolean | NOT NULL, default: true | Can be paused |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

**Validation**:
- days_of_week: array of ints 1-7, non-empty
- time_of_day: valid time
- duration_minutes: 5-120
- content_types: subset of ["vocabulary","reading","grammar","listening"], non-empty
- daily_item_count: 5-50

---

### Lesson

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| schedule_id | UUID | FK → Schedule, NULLABLE | Source schedule (null if manually triggered) |
| date | Date | NOT NULL | Scheduled date |
| status | Enum | NOT NULL, default: pending | See state machine |
| score | Float | NULLABLE | 0.0–1.0 (set on completion) |
| started_at | DateTime | NULLABLE | When user began |
| completed_at | DateTime | NULLABLE | When user finished |
| created_at | DateTime | NOT NULL |

**Uniqueness**: (user_id, date) — one lesson per user per day

**State Machine — LessonStatus**:
```
pending → in_progress → completed
```

---

### LessonItem

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| lesson_id | UUID | FK → Lesson, NOT NULL, indexed | Parent lesson |
| knowledge_segment_id | UUID | FK → KnowledgeSegment, NULLABLE | Source content |
| item_type | Enum | NOT NULL | flashcard, reading, grammar, listening |
| order_index | Integer | NOT NULL | Position in lesson (interleaved) |
| question | Text | NOT NULL | Prompt/question |
| correct_answer | Text | NOT NULL | Expected answer |
| user_response | Text | NULLABLE | What user answered |
| is_correct | Boolean | NULLABLE | Auto-evaluated or self-rated |
| time_spent_seconds | Integer | NULLABLE | How long user spent |
| completed | Boolean | NOT NULL, default: false | Done by user |
| created_at | DateTime | NOT NULL |

**Validation**:
- order_index: ≥ 0, unique within lesson
- item_type: must match content_types from parent Schedule
- is_correct: NULL until user_response is set

---

### SRSCard

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| knowledge_segment_id | UUID | FK → KnowledgeSegment, NULLABLE | Source content (null if document deleted) |
| front | Text | NOT NULL | Question side (word/phrase/prompt) |
| back | Text | NOT NULL | Answer side (definition/translation) |
| ease_factor | Float | NOT NULL, default: 2.5 | SM-2 ease factor (min 1.3) |
| interval_days | Float | NOT NULL, default: 1.0 | Current interval |
| repetitions | Integer | NOT NULL, default: 0 | Successful recall count |
| next_review_date | Date | NOT NULL | When to review next |
| last_review_date | Date | NULLABLE | Last review attempt |
| last_score | Integer | NULLABLE | 1-5 SM-2 rating |
| is_suspended | Boolean | NOT NULL, default: false | Leech (5 consecutive 1s) |
| consecutive_failures | Integer | NOT NULL, default: 0 | Leeche detection counter |
| created_at | DateTime | NOT NULL |

**SM-2 Algorithm Parameters**:
- Rating 5 (perfect): EF += 0.1, interval = interval * EF (new), or interval * EF (review)
- Rating 4 (correct, hesitation): EF unchanged, interval = interval * EF
- Rating 3 (correct, difficulty): EF -= 0.14, interval = interval * EF
- Rating 2 (incorrect, recognized): EF -= 0.22, interval reset to 1, repetitions reset to 0
- Rating 1 (complete blackout): EF -= 0.30, interval reset to 1, repetitions reset to 0, consecutive_failures++
- If consecutive_failures ≥ 5: is_suspended = true (leech)
- Minimum EF = 1.3
- Graduation: first score ≥ 3 graduates from "learning" to "review" state

---

### ProgressSnapshot

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| date | Date | NOT NULL | Snapshot date |
| words_learned | Integer | NOT NULL, default: 0 | Cumulative unique words |
| words_reviewed | Integer | NOT NULL, default: 0 | Reviews today |
| study_minutes | Integer | NOT NULL, default: 0 | Total study time |
| lessons_completed | Integer | NOT NULL, default: 0 | Lessons done today |
| streak_days | Integer | NOT NULL, default: 0 | Consecutive study days |
| accuracy_vocabulary | Float | NULLABLE | 0.0–1.0 |
| accuracy_reading | Float | NULLABLE | 0.0–1.0 |
| accuracy_grammar | Float | NULLABLE | 0.0–1.0 |
| accuracy_listening | Float | NULLABLE | 0.0–1.0 |
| created_at | DateTime | NOT NULL |

**Uniqueness**: (user_id, date)

---

### SyncLog

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NOT NULL, indexed | Owner |
| device_id | UUID | FK → Device, NOT NULL | Source device |
| entity_type | String(50) | NOT NULL | lesson_item, srs_card, progress_snapshot |
| entity_id | UUID | NOT NULL | Affected entity |
| action | Enum | NOT NULL | created, updated, deleted |
| synced_at | DateTime | NOT NULL | When sync occurred |
| conflict_detected | Boolean | NOT NULL, default: false | Was there a conflict? |
| conflict_resolution | String(50) | NULLABLE | lww_remote_win, lww_local_win, manual |
| payload_hash | String(64) | NOT NULL | SHA-256 of synced data |

---

### Donation (Cloud Only, Optional)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | UUID | PK | Unique identifier |
| user_id | UUID | FK → User, NULLABLE | Donor (null if anonymous) |
| platform | Enum | NOT NULL | github_sponsors, ko_fi, open_collective, other |
| amount_cents | Integer | NULLABLE | Donation amount (optional, for transparency) |
| currency | String(3) | NULLABLE | ISO 4217 (optional) |
| platform_transaction_id | String(200) | NULLABLE | External reference |
| is_anonymous | Boolean | NOT NULL, default: false | Hide from public donor list |
| donated_at | DateTime | NOT NULL | When donation occurred |

**Validation**:
- platform: must be one of supported platforms
- amount_cents: ≥ 0 if provided
- Self-hosted: this table is created but may be empty (donations go to project's GitHub Sponsors)

---

## Key Queries & Indexes

| Query | Index | Rationale |
|-------|-------|-----------|
| Documents by user | `(user_id, status)` | List user's docs, filter by status |
| Chunks by document | `(document_id, chunk_index)` | Sequential retrieval for lessons |
| SRS cards due today | `(user_id, next_review_date)` | Daily lesson generation |
| Progress by date range | `(user_id, date)` | Dashboard charts |
| Sync since timestamp | `(user_id, synced_at)` | Pull changes since last sync |
| Lessons by user + date | `(user_id, date)` UNIQUE | One lesson per day |

---

## Data Volume Estimates

| Entity | Per User | At 1,000 Users |
|--------|----------|----------------|
| Documents | 5–50 (avg 15) | 15,000 |
| ContentBlocks | 500–10,000/page (avg 50 blocks × 200 pages × 5 docs) | 50M+ |
| KnowledgeSegments | 200–2,000 (avg 200) | 200,000 |
| SRSCards | 100–5,000 (avg 500) | 500,000 |
| Lessons | 1/day (365/year) | 365,000 |
| LessonItems | 10/day (3,650/year) | 3.65M |
| ProgressSnapshots | 1/day | 365,000 |
| SyncLogs | ~3/device/day | ~3M/year |
