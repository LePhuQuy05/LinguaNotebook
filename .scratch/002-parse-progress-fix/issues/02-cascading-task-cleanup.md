# 02 — Cascading task cleanup on document delete

**What to build:** When a user deletes a document (via UI or `clean-docs.bat`), its Celery task is revoked and purged from the Redis queue, and all related Redis keys are cleaned up. No zombie tasks left behind to block future uploads.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `delete_document()` service function scans the Celery Redis queue for tasks matching the document ID, revokes and removes them
- [ ] `delete_document()` deletes all related Redis keys: `parse:progress:{id}`, `parse:cancel:{id}`
- [ ] `DELETE /api/v1/documents/{id}` returns 200 — verify with `redis-cli KEYS "parse:*"` that no keys remain for the deleted document
- [ ] `DELETE /api/v1/documents/{id}` returns 200 — verify with `redis-cli LLEN celery` that the queue count decreases by 1 if a pending task existed
- [ ] `clean-docs.bat` (both "Delete ALL" and "Delete QUEUED") purges corresponding tasks from Redis after the DB DELETE
- [ ] If a task is already being processed by a worker when the document is deleted, the worker fails gracefully (existing error handling in `_save_content_blocks` handles missing document) — verify no crash or orphaned Redis keys
- [ ] Re-upload the same PDF after deleting → new document gets a fresh task that is picked up immediately (not blocked by stale tasks in queue)
