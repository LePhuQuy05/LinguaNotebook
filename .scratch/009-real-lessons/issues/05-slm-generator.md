# 05 — Offline small-LM generator

**What to build:** A second lesson generator behind the same seam uses the existing offline CPU small-language model to produce richer items. Output is parsed and schema-verified before anything is saved; an error or empty result falls back to the rule generator for that chunk. It is selectable via the generator setting alongside the rule generator. No model installed behaves exactly like rule-only.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] With the generator setting selecting the model, lessons are produced by it
- [ ] Model output is schema-verified before save; malformed/out-of-schema output is discarded
- [ ] An error or empty result falls back to the rule generator for that chunk
- [ ] No model installed → behavior identical to rule-only
- [ ] The model runs offline on the CPU (consistent with ADR-0002); tested via an injected fake adapter
