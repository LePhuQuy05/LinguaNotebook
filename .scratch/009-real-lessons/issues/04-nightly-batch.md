# 04 — Nightly batch generation

**What to build:** The scheduled daily task stops being a stub. It iterates the user's active schedules and, for each whose weekday is active, pre-generates tomorrow's lesson through the existing daily-lesson flow. Running it means a lesson is waiting at the scheduled time without visiting the app; nothing is duplicated for a day that already has a lesson.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Running the task creates tomorrow's lesson for every active schedule on a matching weekday
- [ ] Inactive schedules and off-weekday schedules get nothing
- [ ] A day that already has a lesson is not duplicated
- [ ] The task is idempotent across re-runs
