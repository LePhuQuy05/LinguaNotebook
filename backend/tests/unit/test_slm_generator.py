"""SLM lesson generator tests (feature 009, ticket 05).

The small-LM generator is the second generator behind the seam. With a
chapter context it plans items across the whole chapter in one model pass,
schema-verifies the output, and falls back to the rule generator for any
chunk the model did not cover or produced malformed output for. With no
model file configured it behaves exactly like rule-only.
"""

import asyncio
import json

from src.services import slm_generator
from src.services.item_generators import ItemGenerator, RuleBasedGenerator
from src.services.slm_generator import SlmGenerator


def _chunk(content, chunk_id="c1"):
    return {"chunk_id": chunk_id, "content": content}


def _context(title="天気", chunks=None, plan=None):
    return {
        "chapter_title": title,
        "chunks": chunks or [],
        "plan": plan or [],
        "_cache": {},
    }


def _run(generator, chunk, content_type, context=None):
    """Drive the (async) generator seam synchronously from a plain test."""
    return asyncio.run(generator.generate(chunk, content_type, context))


def _with_model(monkeypatch, output):
    """Point the generator at a fake model file + runtime returning `output`."""
    monkeypatch.setattr(slm_generator, "resolve_model_file", lambda path: "model.gguf")
    monkeypatch.setattr(slm_generator, "get_runtime", lambda path: _FakeRuntime(output))


class _FakeRuntime:
    """A llama-cpp stand-in returning canned model output."""

    def __init__(self, output):
        self.output = output

    def generate(self, prompt, **kwargs):
        return self.output


class TestNoModel:
    def test_implements_the_protocol(self):
        assert isinstance(SlmGenerator(), ItemGenerator)

    def test_without_model_behaves_like_rule_only(self, monkeypatch):
        monkeypatch.setattr(slm_generator, "resolve_model_file", lambda path: None)
        gen = SlmGenerator()
        chunk = _chunk("家族（かぞく）— family")
        assert _run(gen, chunk, "vocabulary") == _run(RuleBasedGenerator(), chunk, "vocabulary")

    def test_without_chapter_context_falls_back_to_rule(self, monkeypatch):
        # Model present but no chapter context → per-chunk rule fallback.
        _with_model(monkeypatch, "[]")
        items = _run(SlmGenerator(), _chunk("内容0"), "vocabulary")
        assert items[0].item_type == "flashcard"
        assert items[0].payload["term"] == "内容0"


class TestChapterPlanning:
    def test_one_model_pass_plans_items_for_every_chunk(self, monkeypatch):
        chunks = [_chunk("学校に通います。", "c1"), _chunk("天気がいいです。", "c2")]
        payload = [
            {
                "passage_index": 0,
                "item_type": "reading",
                "question": "What happens?",
                "correct_answer": "goes to school",
                "data": {
                    "passage": "学校に通います。",
                    "options": ["goes to school", "studies", "sleeps", "eats"],
                    "correct_index": 0,
                },
            },
            {
                "passage_index": 1,
                "item_type": "reading",
                "question": "What is the weather?",
                "correct_answer": "nice",
                "data": {
                    "passage": "天気がいいです。",
                    "options": ["bad", "nice", "ok", "cold"],
                    "correct_index": 1,
                },
            },
        ]
        _with_model(monkeypatch, json.dumps(payload))
        gen = SlmGenerator()
        ctx = _context(chunks=chunks, plan=["reading", "reading"])

        a = _run(gen, chunks[0], "reading", ctx)
        b = _run(gen, chunks[1], "reading", ctx)

        assert a[0].question == "What happens?"
        assert a[0].payload["options"][a[0].payload["correct_index"]] == "goes to school"
        assert b[0].payload["correct_index"] == 1
        assert ctx["_cache"]["_planned"] is True  # single planning pass

    def test_correct_answer_normalized_to_option_text(self, monkeypatch):
        chunks = [_chunk("学校に通います。", "c1")]
        payload = [
            {
                "passage_index": 0,
                "item_type": "reading",
                "question": "Q",
                "correct_answer": "WRONG",
                "data": {"passage": "p", "options": ["a", "correct", "c", "d"], "correct_index": 1},
            }
        ]
        _with_model(monkeypatch, json.dumps(payload))

        item = _run(
            SlmGenerator(), chunks[0], "reading", _context(chunks=chunks, plan=["reading"])
        )[0]

        # display + grading must agree on the chosen option text
        assert item.correct_answer == "correct"
        assert item.payload["options"][item.payload["correct_index"]] == "correct"

    def test_malformed_json_falls_back_to_rule(self, monkeypatch):
        chunks = [_chunk("内容0", "c1")]
        _with_model(monkeypatch, "definitely not json")
        items = _run(SlmGenerator(), chunks[0], "vocabulary", _context(chunks=chunks))
        assert items[0].item_type == "flashcard"
        assert items[0].payload["term"] == "内容0"

    def test_schema_violation_is_dropped_and_falls_back_to_rule(self, monkeypatch):
        chunks = [_chunk("内容0", "c1")]
        # only two options → out of schema
        payload = [
            {
                "passage_index": 0,
                "item_type": "reading",
                "question": "Q",
                "correct_answer": "x",
                "data": {"passage": "p", "options": ["a", "b"], "correct_index": 0},
            }
        ]
        _with_model(monkeypatch, json.dumps(payload))
        items = _run(SlmGenerator(), chunks[0], "reading", _context(chunks=chunks))
        # The model's two-option entry was dropped → the rule generator made
        # the reading item, carrying the whole chunk as its passage.
        assert items[0].item_type == "reading"
        assert items[0].payload["passage"] == "内容0"

    def test_uncovered_chunk_falls_back_to_rule(self, monkeypatch):
        chunks = [_chunk("学校に通います。", "c1"), _chunk("内容0", "c2")]
        payload = [
            {
                "passage_index": 0,
                "item_type": "reading",
                "question": "Q",
                "correct_answer": "goes to school",
                "data": {
                    "passage": "p",
                    "options": ["goes to school", "a", "b", "c"],
                    "correct_index": 0,
                },
            }
        ]
        _with_model(monkeypatch, json.dumps(payload))
        gen = SlmGenerator()
        ctx = _context(chunks=chunks, plan=["reading", "vocabulary"])

        first = _run(gen, chunks[0], "reading", ctx)
        second = _run(gen, chunks[1], "vocabulary", ctx)

        assert first[0].item_type == "reading"
        assert second[0].item_type == "flashcard"  # rule fallback for the gap


class TestRealOutputShapes:
    """Shapes the 1.7B model actually emits (validated live on Qwen3-1.7B):
    a per-passage `=> [single-array]` block mirroring the example, and
    trailing commentary after the closing bracket."""

    def test_per_passage_arrays_are_merged_by_index(self, monkeypatch):
        chunks = [_chunk("家族（かぞく）— family", "c1"), _chunk("雨（あめ）— rain", "c2")]
        raw = (
            "[0] (flashcard)\n家族（かぞく）— family\n"
            '=> [{"passage_index":0,"item_type":"flashcard","question":"Q",'
            '"correct_answer":"family","data":{"term":"家族","reading":"かぞく",'
            '"definition":"family","example":"家族は大切です。"}}]\n'
            "[1] (flashcard)\n雨（あめ）— rain\n"
            '=> [{"passage_index":1,"item_type":"flashcard","question":"Q",'
            '"correct_answer":"rain","data":{"term":"雨","reading":"あめ",'
            '"definition":"rain","example":""}}]\n'
        )
        _with_model(monkeypatch, raw)
        gen = SlmGenerator()
        ctx = _context(chunks=chunks, plan=["vocabulary", "vocabulary"])

        first = _run(gen, chunks[0], "vocabulary", ctx)
        second = _run(gen, chunks[1], "vocabulary", ctx)

        assert first[0].payload["term"] == "家族"
        assert second[0].payload["term"] == "雨"

    def test_trailing_commentary_is_ignored(self, monkeypatch):
        chunks = [_chunk("天気（てんき）— weather", "c1")]
        raw = (
            '[{"passage_index":0,"item_type":"flashcard","question":"Q",'
            '"correct_answer":"weather","data":{"term":"天気","reading":"てんき",'
            '"definition":"weather","example":""}}]\n'
            "Okay, let me double-check that the weather term is correct..."
        )
        _with_model(monkeypatch, raw)

        item = _run(SlmGenerator(), chunks[0], "vocabulary", _context(chunks=chunks))[0]

        assert item.payload["term"] == "天気"
        assert item.correct_answer == "weather"


class TestDispatcher:
    def test_slm_setting_selects_slm_generator(self, monkeypatch):
        monkeypatch.setattr("src.services.item_generators.settings.lesson_generator", "slm")
        from src.services.item_generators import get_item_generator

        assert isinstance(get_item_generator(), SlmGenerator)

    def test_both_setting_still_falls_back_to_rule(self, monkeypatch):
        # Ticket 06 wires `both` (two comparable lessons); until then rule.
        monkeypatch.setattr("src.services.item_generators.settings.lesson_generator", "both")
        from src.services.item_generators import get_item_generator

        assert isinstance(get_item_generator(), RuleBasedGenerator)
