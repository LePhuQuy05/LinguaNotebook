# 06 — Provenance + A/B compare

**What to build:** Every lesson records which generator produced it. When the generator setting is "both", two lessons for the same chapter and date are generated — one per generator — and the daily view shows both with a rule/SLM switcher; completing one discards the other. This lets the user experience both generators and choose which to keep, after which the setting is switched to the winner.

**Blocked by:** 02, 05

**Status:** ready-for-agent

- [ ] Every lesson records its generator (provenance)
- [ ] In "both" mode, the daily view returns two lessons for the same chapter+date with a switcher
- [ ] Completing one lesson discards the other
- [ ] Switching the generator setting to a single generator stops producing the loser
- [ ] Coverage ≥80% at the lesson-service seam
