# 01 — Progress heartbeat on task pickup

**What to build:** User uploads PDF, worker picks up task → frontend shows "Parsing... Page 0 of N" instantly instead of "unknown" for 50+ seconds while the first page processes.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Worker writes initial `{"status":"running","current_page":0,"total_pages":N}` to Redis immediately after receiving task and before parsing page 1 (N = actual page count after applying start/end constraints)
- [ ] Worker updates document DB status from `queued` to `parsing` when it begins work
- [ ] Frontend `ParseProgress` component renders the progress bar (not "Waiting for worker") as soon as the poll endpoint returns `status: "running"` — verify this is already handled
- [ ] Verify end-to-end: upload PDF → start worker → `GET /api/v1/documents/{id}/parse/progress/poll` returns `{"status":"running","current_page":0,"total_pages":N}` within 5 seconds of worker picking up the task
- [ ] Verify that after page 1 completes, `current_page` advances to 1 and progress bar updates accordingly
