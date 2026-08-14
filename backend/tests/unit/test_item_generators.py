"""Item generator tests — the generator seam (009-01).

The rule-based generator is the always-on floor behind the seam:
vocabulary chunks become structured flashcards, other content types
become four-option multiple-choice items, and an empty chunk is
skipped. The dispatcher resolves the active generator from the
LESSON_GENERATOR setting, defaulting to "rule".
"""

import asyncio

from src.services.item_generators import (
    ItemGenerator,
    RuleBasedGenerator,
    get_item_generator,
)


def _chunk(content, chunk_id="c1"):
    return {"chunk_id": chunk_id, "content": content}


def _run(generator, chunk, content_type):
    """Drive the (async) generator seam synchronously from a plain test."""
    return asyncio.run(generator.generate(chunk, content_type))


class TestRuleGenerator:
    def test_implements_the_protocol(self):
        assert isinstance(RuleBasedGenerator(), ItemGenerator)

    def test_empty_chunk_is_skipped(self):
        assert _run(RuleBasedGenerator(), _chunk(""), "vocabulary") == []

    def test_unknown_content_type_degrades_to_flashcard(self):
        # Unknown content types fall back to the flashcard safe default,
        # so the lesson service's ItemType(...) never sees a bad value.
        items = _run(RuleBasedGenerator(), _chunk("内容0"), "mystery")
        assert len(items) == 1
        assert items[0].item_type == "flashcard"
        assert items[0].payload["term"] == "内容0"


class TestFlashcard:
    def test_structured_vocab_entry_is_parsed(self):
        items = _run(RuleBasedGenerator(), _chunk("家族（かぞく）— family"), "vocabulary")
        assert len(items) == 1
        item = items[0]
        assert item.item_type == "flashcard"
        assert item.question == "What does this term mean?"
        assert item.payload["term"] == "家族"
        assert item.payload["reading"] == "かぞく"
        assert item.payload["definition"] == "family"
        assert item.correct_answer == "family"

    def test_table_row_is_parsed(self):
        content = "| 家族 | かぞく | family |"
        item = _run(RuleBasedGenerator(), _chunk(content), "vocabulary")[0]
        assert item.payload["term"] == "家族"
        assert item.payload["reading"] == "かぞく"
        assert item.payload["definition"] == "family"

    def test_plain_chunk_falls_back_to_whole_content(self):
        item = _run(RuleBasedGenerator(), _chunk("内容0"), "vocabulary")[0]
        assert item.payload["term"] == "内容0"
        assert item.payload["definition"] == ""
        assert item.correct_answer == "内容0"

    def test_example_key_present(self):
        item = _run(RuleBasedGenerator(), _chunk("家族（かぞく）— family"), "vocabulary")[0]
        assert "example" in item.payload

    def test_example_sentence_extracted_from_following_lines(self):
        content = "家族（かぞく）— family\n家族は大切です。"
        item = _run(RuleBasedGenerator(), _chunk(content), "vocabulary")[0]
        assert item.payload["term"] == "家族"
        assert item.payload["example"] == "家族は大切です。"


class TestMultipleChoice:
    def test_reading_has_passage_four_options_and_correct_index(self):
        content = "家族は大切です。一緒に旅行します。毎日電話します。週末に会います。"
        item = _run(RuleBasedGenerator(), _chunk(content), "reading")[0]
        assert item.item_type == "reading"
        payload = item.payload
        assert payload["passage"] == content
        assert len(payload["options"]) == 4
        assert payload["options"][payload["correct_index"]] == item.correct_answer
        # four real sentences, no padded fillers needed
        sentences = [
            "家族は大切です。",
            "一緒に旅行します。",
            "毎日電話します。",
            "週末に会います。",
        ]
        assert set(payload["options"]) == set(sentences)

    def test_short_chunk_is_padded_to_four_options(self):
        item = _run(RuleBasedGenerator(), _chunk("短い文です。"), "reading")[0]
        assert len(item.payload["options"]) == 4
        assert item.payload["options"][item.payload["correct_index"]] == item.correct_answer

    def test_grammar_has_pattern_prompt_and_options(self):
        item = _run(RuleBasedGenerator(), _chunk("私は毎日学校に行きます。"), "grammar")[0]
        payload = item.payload
        assert payload["pattern"] == "に"
        assert "___" in payload["prompt"]
        assert len(payload["options"]) == 4
        assert payload["options"][payload["correct_index"]] == "に"
        assert item.correct_answer == "に"

    def test_grammar_without_particle_degrades_to_sentence_mc(self):
        item = _run(RuleBasedGenerator(), _chunk("単語だけ"), "grammar")[0]
        assert "options" in item.payload
        assert len(item.payload["options"]) == 4

    def test_listening_has_text_audio_key_and_options(self):
        content = "今日はいい天気です。散歩します。"
        item = _run(RuleBasedGenerator(), _chunk(content), "listening")[0]
        assert item.item_type == "listening"
        payload = item.payload
        assert payload["text"] == content
        assert "audio_key" in payload
        assert len(payload["options"]) == 4
        assert payload["options"][payload["correct_index"]] == item.correct_answer

    def test_option_order_is_deterministic_for_the_same_chunk(self):
        content = "家族は大切です。一緒に旅行します。毎日電話します。週末に会います。"
        generator = RuleBasedGenerator()
        first = _run(generator, _chunk(content), "reading")[0].payload["options"]
        second = _run(generator, _chunk(content), "reading")[0].payload["options"]
        assert first == second


class TestDispatcher:
    def test_defaults_to_rule_generator(self, monkeypatch):
        monkeypatch.setattr("src.services.item_generators.settings.lesson_generator", "rule")
        assert isinstance(get_item_generator(), RuleBasedGenerator)

    def test_slm_setting_selects_slm_generator(self, monkeypatch):
        # Ticket 05: "slm" plugs in the whole-chapter small-LM generator
        # (asserted in test_slm_generator.py); "both" still degrades to the
        # rule floor until ticket 06 builds two comparable lessons.
        monkeypatch.setattr("src.services.item_generators.settings.lesson_generator", "both")
        assert isinstance(get_item_generator(), RuleBasedGenerator)
