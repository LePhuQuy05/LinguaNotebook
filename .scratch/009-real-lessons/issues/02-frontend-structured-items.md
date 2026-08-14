# 02 — Frontend renders structured items

**What to build:** The learning screen renders each item from its structured payload: a real flashcard (term/reading/definition/example), a reading passage with four clickable options, a grammar fill with four options, and a listening item that plays its audio and shows four options. Selecting an option submits that option's index. Items without the payload (old ones) keep today's rendering.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] Each of the four item types renders its structured form from `data`
- [ ] Option buttons submit the selected index; the flashcard still collects a self-rating
- [ ] Listening items play their audio
- [ ] Old items without `data` render exactly as before
- [ ] Frontend typecheck + lint pass
