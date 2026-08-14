"""SLM escalation for curriculum extraction (spec 008, ticket 03).

Guards the escalation contract: it triggers only below the confidence gate,
feeds only the isolated TOC pages + Known pages to the model (never the
whole book), and makes a hallucinated page impossible — every page must be
a member of Known pages, enforced at verification ("reason free, constrain
late"). The real model adapter is gated on a model file; these tests use a
fake LLM / injected escalator so the suite never touches llama-cpp-python.
"""

import pytest

from src.services.curriculum_escalation import (
    _build_prompt,
    _resolve_model_file,
    _verify_and_finalize,
    build_curriculum_escalator,
)


def _toc_markdown() -> str:
    return (
        "--- Page 4 ---\n"
        "1課 人間関係 .....20\n"
        "2課 天気 .....76\n"
        "--- Page 20 ---\n"
        "## 1課 人間関係\n本文はこちらにあります。秘密の本文。\n"
        "--- Page 76 ---\n"
        "## 2課 天気\n本文。\n"
    )


class TestBuildPrompt:
    """Only the isolated TOC pages reach the model, plus the Known-pages
    whitelist — never the whole book."""

    def test_includes_toc_pages_and_allowed_pages(self):
        markdown = _toc_markdown()
        prompt = _build_prompt(markdown, {4}, [4, 20, 76])

        # TOC page content present, body-page content absent
        assert "1課 人間関係" in prompt
        assert "秘密の本文" not in prompt
        # The allowed-page whitelist is spelled out
        assert "4, 20, 76" in prompt

    def test_prompt_demands_one_entry_per_line_format(self):
        prompt = _build_prompt(_toc_markdown(), {4}, [4, 20, 76])

        assert "<number>|<title>|<page>" in prompt


class TestVerifyAndFinalize:
    """Parse → validate → whitelist membership → monotonic order →
    sequential numbering. Page ranges are computed later in code."""

    def test_valid_output_becomes_sequential_entries(self):
        raw = "1|あいさつ|5\n2|天気|76\n3|動詞|100\n"

        entries = _verify_and_finalize(raw, [5, 76, 100])

        assert entries == [
            {"part": "", "chapter_num": 1, "chapter_title": "あいさつ", "page": 5},
            {"part": "", "chapter_num": 2, "chapter_title": "天気", "page": 76},
            {"part": "", "chapter_num": 3, "chapter_title": "動詞", "page": 100},
        ]

    def test_page_outside_known_pages_is_dropped(self):
        """A hallucinated page can never survive: 99 is not a Known page."""
        raw = "1|あいさつ|5\n2|でたらめ|99\n3|天気|76\n"

        entries = _verify_and_finalize(raw, [5, 76])

        assert [e["page"] for e in entries] == [5, 76]
        assert all(e["chapter_title"] != "でたらめ" for e in entries)

    def test_out_of_order_input_is_sorted_monotonically(self):
        raw = "1|天気|76\n2|あいさつ|5\n"

        entries = _verify_and_finalize(raw, [5, 76])

        assert [e["page"] for e in entries] == [5, 76]
        assert [e["chapter_title"] for e in entries] == ["あいさつ", "天気"]

    def test_malformed_lines_skipped(self):
        raw = (
            "note the curriculum\n"
            "1|あいさつ|5\n"
            "broken line without pipes\n"
            "|no number|7\n"
            "2|天気|76\n"
        )

        entries = _verify_and_finalize(raw, [5, 76])

        assert [(e["chapter_num"], e["chapter_title"]) for e in entries] == [
            (1, "あいさつ"),
            (2, "天気"),
        ]

    def test_duplicate_title_page_rows_collapse(self):
        raw = "1|あいさつ|5\n2|あいさつ|5\n3|天気|76\n"

        entries = _verify_and_finalize(raw, [5, 76])

        assert len(entries) == 2

    def test_empty_or_none_raw_yields_empty(self):
        assert _verify_and_finalize("", [5, 76]) == []
        assert _verify_and_finalize(None, [5, 76]) == []


class TestBuildEscalator:
    """No model file → no escalation (graceful degradation, ticket 04)."""

    def test_no_path_configured_returns_none(self, monkeypatch):
        from src.core.config import settings

        monkeypatch.setattr(settings, "curriculum_llm_path", "")

        assert build_curriculum_escalator() is None

    def test_path_without_model_file_returns_none(self, monkeypatch, tmp_path):
        from src.core.config import settings

        monkeypatch.setattr(settings, "curriculum_llm_path", str(tmp_path / "missing"))

        assert build_curriculum_escalator() is None

    def test_model_file_present_builds_callable(self, monkeypatch, tmp_path):
        """A directory containing a .gguf resolves to the file; the returned
        escalator uses the (fake) LLM's output, verified against Known pages."""
        from src.core.config import settings
        from src.services import curriculum_escalation

        model_dir = tmp_path / "curriculum-llm"
        model_dir.mkdir()
        (model_dir / "qwen3-1.7b-q4_k_m.gguf").write_text("not a real model")

        monkeypatch.setattr(settings, "curriculum_llm_path", str(model_dir))

        class FakeLLM:
            def generate(self, prompt):
                return "1|あいさつ|20\n2|天気|76\n"

        monkeypatch.setattr(curriculum_escalation, "_get_llm", lambda _path: FakeLLM())

        escalate = build_curriculum_escalator()
        assert escalate is not None

        entries = escalate(_toc_markdown(), {4}, [4, 20, 76])

        assert [e["page"] for e in entries] == [20, 76]
        assert [e["chapter_num"] for e in entries] == [1, 2]

    def test_llm_returns_hallucinated_page_still_dropped(self, monkeypatch, tmp_path):
        """Even a misbehaving model cannot inject a page outside Known pages."""
        from src.core.config import settings
        from src.services import curriculum_escalation

        model_dir = tmp_path / "curriculum-llm"
        model_dir.mkdir()
        (model_dir / "model.gguf").write_text("x")
        monkeypatch.setattr(settings, "curriculum_llm_path", str(model_dir))

        class FakeLLM:
            def generate(self, prompt):
                return "1|あいさつ|99\n2|天気|20\n"

        monkeypatch.setattr(curriculum_escalation, "_get_llm", lambda _path: FakeLLM())

        escalate = build_curriculum_escalator()
        entries = escalate(_toc_markdown(), {4}, [4, 20, 76])

        assert [e["page"] for e in entries] == [20]


def _model_file_configured() -> bool:
    """True when a real .gguf is configured — gates the integration test."""
    from src.core.config import settings

    return _resolve_model_file(settings.curriculum_llm_path) is not None


_model_gate = pytest.mark.skipif(
    not _model_file_configured(),
    reason="no .gguf at CURRICULUM_LLM_PATH — real-model test skipped (ticket 04)",
)


@_model_gate
def test_real_model_end_to_end():
    """Ticket 04's gated integration test: with a real model present, the
    escalator recovers entries from the golden TOC; every page is a Known
    page (hallucination impossible), ordering is monotonic, numbering
    sequential. Skips silently when no model is installed."""
    markdown = _toc_markdown()
    escalator = build_curriculum_escalator()
    assert escalator is not None

    entries = escalator(markdown, {4}, [4, 20, 76])

    assert entries, "model produced no curriculum entries"
    pages = [e["page"] for e in entries]
    assert all(p in {4, 20, 76} for p in pages)  # whitelist enforced in code
    assert pages == sorted(pages)
    assert [e["chapter_num"] for e in entries] == list(range(1, len(entries) + 1))
