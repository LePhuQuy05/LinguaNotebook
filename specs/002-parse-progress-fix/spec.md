# Spec: Fix Parse Progress Tracking & Task Lifecycle

**Status**: ready-for-agent  
**Created**: 2026-07-28  
**Parent**: 001-lingua-notebook  
**Triage**: ready-for-agent

## Problem Statement

Users uploading PDFs for OCR parsing experience three related failures:

1. **"Unknown" status on frontend**: After uploading a PDF and starting the GPU worker, the frontend displays "unknown / Page 0 of 0" for 50+ seconds until the first page completes. During this window, users believe the system is broken and repeatedly restart the worker or re-upload the document.

2. **Stale Celery tasks accumulate**: When a user deletes a document (via `clean-docs.bat` or API), the corresponding Celery task is NOT removed from the Redis broker queue. Over multiple upload-delete cycles, stale tasks pile up. The worker (`--concurrency=1`) processes these zombie tasks for already-deleted documents while the real document's task sits waiting in the queue.

3. **No document status transition**: The document remains `queued` in the database even after the worker has picked up and started processing it. The frontend relies on this status to decide whether to show the progress component, creating a fragile dependency on Redis state that may not exist yet.

## Solution

Three targeted fixes to make the parse progress pipeline reliable:

1. **Initial progress heartbeat**: Worker writes an initial `{"status": "running", "current_page": 0}` progress entry to Redis immediately upon receiving a task — before downloading the PDF or loading any pages. The frontend sees "running" instantly instead of "unknown".

2. **Document status transition**: Worker updates the document's DB status from `queued` to `parsing` when it begins work. The frontend already handles `parsing` status — this just makes it consistent.

3. **Cascading task cleanup**: When a document is deleted, its Celery task is revoked and purged from the Redis queue. No more zombie tasks.

## User Stories

1. As a language learner uploading a PDF, I want to see "Parsing..." with a progress bar immediately after the worker picks up my document, so that I know the system is working and I don't need to restart anything.

2. As a language learner, I want the document status to change from "queued" to "parsing" when the worker starts, so that I can distinguish between "waiting for a worker" and "actively being processed."

3. As a language learner deleting a document, I want its queued parsing task to be cancelled automatically, so that I don't waste GPU time on documents I no longer need.

4. As a language learner re-uploading the same PDF after deleting it, I want the new upload to be processed immediately without stale tasks blocking the queue.

5. As a developer debugging parse issues, I want to see a clear audit trail in Redis: initial progress → per-page progress → completion, so that I can diagnose where a parse got stuck.

6. As a self-hoster running the app on CPU-only, I want the same progress visibility as GPU users, so that I'm not left wondering whether the worker is alive during long parse times.

## Implementation Decisions

### 1. Progress initialization before first page

**Decision**: In `parse_pdf_task`, after downloading the PDF and determining the total page count, write an initial progress record to Redis with `current_page: 0` and `status: "running"` BEFORE calling `parser.parse_pdf()`.

**Rationale**: The `_progress_callback` is only invoked by `HPDFParser.parse_pdf()` after each page completes. On GPU (Intel Arc), page 1 takes ~50 seconds. On CPU, it takes 2-3 minutes per page. Without an initial write, the Redis key doesn't exist during this entire window, and the API returns `{"status": "unknown"}`.

**Key detail**: The `total_pages` field must reflect the actual page count AFTER applying `page_start`/`page_end` constraints, so the frontend shows the correct denominator immediately.

### 2. Document status: queued → parsing

**Decision**: The worker updates the document's `status` column from `queued` to `parsing` when it begins processing. The `DocumentStatus` enum already has a `parsing` value — this change just adds the write at the right time.

**Rationale**: The frontend's `DocumentViewerPage` already checks for `doc.status === "parsing"` on line 96 when deciding to render `ParseProgress`. No frontend changes needed.

### 3. Cascading task cleanup on document delete

**Decision**: `parser_service.delete_document()` is extended to:
- Look up the document
- Revoke any pending Celery task for that document from the Redis queue
- Clean up associated Redis keys (`parse:progress:{id}`, `parse:cancel:{id}`)
- Then delete the document from DB

**Implementation approach**: Before deleting the document record, scan the Celery queue for tasks whose `argsrepr` contains the document ID. Remove matching tasks. This is a best-effort cleanup — if the task is already being processed by a worker, it will fail gracefully when it can't find the document in DB (the existing error handling already covers this).

### 4. Frontend: handle "running" with 0 progress

**Decision**: The `ParseProgress` component already handles `current_page: 0` gracefully — it shows "Page 0 of N" with a 0% progress bar. No changes needed.

**Confirmation**: The component's null-check at line 60-69 only triggers when `progress` state is `null` (initial React state before first poll response). Once the API returns `{"status": "running", "current_page": 0, ...}`, `progress` is set and the progress bar renders.

### 5. Redis key lifecycle

**Decision**: All parse-related Redis keys follow this lifecycle:

```
parse:progress:{doc_id}  → created at task start (TTL 3600s) → updated per page → updated at completion
parse:cancel:{doc_id}    → created on user cancel (TTL 3600s) → checked per page → deleted on task end
celery queue entry       → created on upload → deleted on worker pickup OR document delete
```

## Testing Decisions

### What makes a good test

- Test the external API contract, not internal Redis key formats
- Use the existing HTTP endpoints as the test seam
- Verify behavior changes, not implementation details

### Test cases

| # | Test | Seam | Expected |
|---|------|------|----------|
| 1 | Poll progress immediately after upload + worker pickup | `GET .../poll` | Returns `{"status": "running", "current_page": 0, "total_pages": N}` within 5 seconds of worker receiving task |
| 2 | Delete document with pending task | `DELETE /api/v1/documents/{id}` | Returns 200, document gone from DB, task gone from Celery queue |
| 3 | Delete document with active parse | `DELETE` + `GET .../poll` | Returns 200, worker stops processing within one page |
| 4 | Re-upload after delete | `POST /upload` → `GET .../poll` | New document gets fresh task, progresses normally |
| 5 | Document status transitions | `GET /api/v1/documents/{id}` | `queued` → `parsing` (worker starts) → `completed` (finishes) |

### Prior art

- The existing `test_model.py` shows the pattern of testing the HPD model in isolation
- The existing curl-based testing from the debugging session demonstrates the API-level seam
- SQL injection audit with sqlmap established the pattern of external tool validation

## Out of Scope

- **Celery result backend changes**: This spec only touches the broker (Redis queue), not the result backend
- **Worker concurrency increase**: `--concurrency=1` remains the default for GPU stability
- **Frontend polling interval changes**: The 1-second poll interval is unchanged
- **Real-time push (WebSocket/SSE)**: Polling remains the progress mechanism; SSE endpoint exists but is unused by the current frontend
- **Multi-GPU or distributed workers**: Single-worker architecture is unchanged
- **Progress persistence across Redis restarts**: Redis data is ephemeral; lost progress on restart is acceptable

## Further Notes

- The stale task accumulation bug was discovered during a real debugging session where 7 duplicate tasks for the same PDF (different document IDs) were found in the Redis queue, with only 1 corresponding document still in the DB.
- The "unknown" symptom was traced to a 53-second gap between worker task receipt and first `_progress_callback` invocation for the Shinkanzen N3 PDF (186 pages, DPI 100).
- The fix for initial progress requires the worker to open the PDF briefly to count pages BEFORE starting the parse loop. This adds ~0.1s overhead (PyMuPDF `fitz.open()` is fast) and is well worth the UX improvement.
- The cascading task cleanup is best-effort: if a task is already executing when the document is deleted, the worker will fail when trying to save results to a non-existent document. The existing `try/except` in `_save_content_blocks` handles this gracefully.
