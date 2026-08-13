# 02 — Wire parse → embed (make the knowledge base live)

**What to build:** The RAG stage is not connected: `embed_document` exists but nothing dispatches it, so Qdrant is empty and `hybrid_search` returns nothing. After parse saves ContentBlocks, the worker dispatches `embed_document`; that task chunks the blocks, embeds them (BGE-M3 dense + BM25 sparse), and upserts into the user's Qdrant collection. The embed worker must use the persistent `_get_event_loop()` pattern from `parse_worker` — its current per-call `new_event_loop()`/`close()` has the same "proactor.send on None" crash on the second document in one process.

**Blocked by:** 01 (blocks must be clean before indexing)

**Status:** ready-for-human

- [x] `parse_pdf_task` dispatches `embed_document` after blocks are saved (only when parse succeeded)
- [x] Embed worker runs chunk + embed + upsert on the persistent event loop — two documents processed sequentially in one worker process both succeed
- [x] E2E: parse a scanned PDF → Qdrant collection has points → `hybrid_search` returns results with content
- [x] Regression test: `embed_worker` uses the same loop identity pattern as `parse_worker` (loop never closed)
- [x] Worker log reports blocks → chunks indexed

## Comments

2026-08-14 — completed, live-verified. Embed dispatch is wired in `parse_worker._dispatch_embed`; the embed worker runs on the shared persistent loop and now publishes Redis `embed:progress:<doc_id>` frames (initial, per-batch, final) and persists `embed_status`/`chunks_count`/`embedded_at` on the `Document`. Real doc `16116abe` (3693 blocks): 2545 Qdrant points, `hybrid_search` returns page-accurate hits. Tests: `test_embed_worker.py` (loop identity, status writes on success/failure, Redis frames), `test_embed_service.py` (progress callback per batch).

2026-08-13 — Implemented + committed (1825bbe): parse_worker dispatches
`embed_document_task.delay(document_id=..., user_id=None)` after blocks save;
embed_worker resolves user_id from the Document when None and runs on the
shared persistent loop (`src.utils.worker_loop.get_event_loop`), never closed.
BGE-M3 pinned to `device="cpu"` (XPU OOM on encode). Embed E2E still in
progress: re-running the embed for GOI doc efcca81d after the Docker stack
was down (Qdrant at 0 points); worker log will confirm blocks → chunks indexed.
