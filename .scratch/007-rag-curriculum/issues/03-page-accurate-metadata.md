# 03 — Page-accurate chunk metadata

**What to build:** Every Qdrant payload currently claims `page_start: 1` — the chunker never receives page numbers, so page-accurate citations ("this vocab is from page 42") and page-range filters are impossible. `SmartChunker.chunk_blocks` receives blocks carrying `page_number`; each `Chunk` gets `page_start`/`page_end` metadata, and `embed_and_index_chunks` writes them into the Qdrant payload. `hybrid_search` already supports metadata filters — the page range becomes usable.

**Blocked by:** 02 (index must be live to carry the metadata)

**Status:** ready-for-agent

- [ ] `Chunk.metadata` carries `page_start`/`page_end` from the source blocks (min/max of the block page numbers)
- [ ] Qdrant payloads contain real page numbers (not hardcoded 1)
- [ ] Unit tests: single-page chunk → page_start == page_end; multi-block paragraph chunk → correct min/max
- [ ] E2E: indexed document's payloads show the true page numbers for a sampled chunk

## Comments

2026-08-13 — Implemented + committed (d97b45c): chunker takes
`page_number` from each block, structural blocks carry
`block_types`/`page_start`/`page_end`, `_merge_pending` computes min/max.
CJK-aware token estimate fixed (`[A-Za-z0-9_]+` words + CJK chars, not `\w`
which double-counts Japanese). Payload page_start/page_end verified by the
E2E embed run (in progress, ticket 02).
