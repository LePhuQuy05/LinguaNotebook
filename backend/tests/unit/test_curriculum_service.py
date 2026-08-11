"""Curriculum map extraction tests.

Golden fixture: the real Shinkanzen N3 TOC (pages 4-5 of the 2026-08-11
PaddleOCR parse, document 16116abe). The extractor must find 第1部/第2部
parts, chapters with dotted page numbers, and resolve page ranges —
conservatively, with practice/mock sections bridged.
"""

from pathlib import Path

from src.services.curriculum_service import extract_curriculum

FIXTURE = Path(__file__).parent.parent / "fixtures" / "shinkanzen_n3_toc_real.md"


def load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


class TestGoldenFixture:
    def test_finds_parts_and_chapters(self):
        rows = extract_curriculum(load_fixture())

        assert len(rows) >= 10
        assert rows[0]["part"].startswith("第1部")
        assert all(row["part"].startswith("第1部") for row in rows[:8])

    def test_weather_chapter_lands_on_page_76(self):
        """18課 自然1：季節と天気、地理 .....76 (printed page → PDF page)."""
        rows = extract_curriculum(load_fixture())
        weather = [r for r in rows if "天気" in r["chapter_title"]]

        assert weather, "weather chapter not extracted"
        assert weather[0]["page_start"] == 76

    def test_ranges_bridge_practice_sections(self):
        """Chapter 5 (.....18) ends at 23; chapter 6 starts at 24 — the
        実力を試そう practice (22-23) is bridged, not counted as a chapter."""
        rows = extract_curriculum(load_fixture())
        by_start = {r["page_start"]: r for r in rows}

        assert 18 in by_start
        assert 24 in by_start
        assert by_start[18]["page_end"] == 23

    def test_ranges_are_increasing_and_non_overlapping(self):
        rows = extract_curriculum(load_fixture())

        for a, b in zip(rows, rows[1:]):
            assert a["page_start"] < b["page_start"]
            assert a["page_end"] < b["page_start"]

    def test_part_two_boundary_handled(self):
        """The OCR merges 第2部 into a chapter line ('32課 第2部...') —
        later chapters must carry part=第2部."""
        rows = extract_curriculum(load_fixture())
        part2 = [r for r in rows if r["part"].startswith("第2部")]

        assert part2, "no 第2部 chapters found"
        assert all(r["page_start"] > 100 for r in part2)


class TestSynthetic:
    def test_simple_toc(self):
        markdown = (
            "--- Page 4 ---\n"
            "第1部 話題別\n"
            "1課 人・体 .....14\n"
            "2課 天気 .....20\n"
            "--- Page 5 ---\n"
            "3課 学校 .....26\n"
        )
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["page_start"], r["page_end"]) for r in rows] == [
            (1, 14, 19),
            (2, 20, 25),
            (3, 26, 26),
        ]

    def test_missing_page_number_drops_entry(self):
        markdown = "--- Page 4 ---\n第1部 話題別\n1課 人・体\n本文なし\n"
        assert extract_curriculum(markdown) == []

    def test_practice_sections_skipped(self):
        markdown = (
            "--- Page 4 ---\n"
            "第1部 話題別\n"
            "1課 人・体 .....14\n"
            "実力を試そう（1課～5課）.....22\n"
            "2課 天気 .....24\n"
        )
        rows = extract_curriculum(markdown)

        assert [r["chapter_num"] for r in rows] == [1, 2]
        assert rows[0]["page_end"] == 23  # bridges the practice section

    def test_mixed_kanji_lesson_marker(self):
        """OCR emits both 課 and 课 (simplified) for the lesson marker."""
        markdown = "--- Page 4 ---\n第1部 話題別\n17课 社会3：行事 .....72\n"
        rows = extract_curriculum(markdown)

        assert rows[0]["chapter_num"] == 17
        assert rows[0]["page_start"] == 72

    def test_absent_toc_returns_empty(self):
        assert extract_curriculum("--- Page 1 ---\nただの本文です。\n") == []
