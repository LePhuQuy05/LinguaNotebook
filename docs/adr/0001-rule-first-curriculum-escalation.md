# 0001 — Curriculum extraction is rule-first, with an optional small-LM escalation

The curriculum extractor stays deterministic and rule-based by default; an offline small-language-model fallback runs only when the rule scan's confidence is below the gate (< 0.3). The LM runs inside the parse worker via `asyncio.to_thread` (the worker's persistent event loop is never blocked), reads a manually-downloaded GGUF from `CURRICULUM_LLM_PATH` (default `backend/model/curriculum-llm/`), and degrades gracefully to the empty-map fallback when no model is present.

Why: the app is fully offline and self-hostable, the common case (well-formed TOCs) is served by rules at zero runtime cost and is unit-testable, and a ~1.3–2.6 GB model download must not be forced on every self-hoster. The LM is an escalation layer, not the default path — it covers the messy TOCs the heuristics can't read.
