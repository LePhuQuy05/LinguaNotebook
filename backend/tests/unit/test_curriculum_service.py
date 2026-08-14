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


class TestBodyHeadings:
    """Fallback path: a book whose chapters are body headings (## N章),
    e.g. the Shinkanzen N3 Kanji book, which has no 課 TOC to scan."""

    def test_kanji_book_style_chapters(self):
        """## N章 headings with OCR space variants (## 3 章料理) become
        chapters; page ranges come from the pages the headings appear on."""
        markdown = (
            "--- Page 8 ---\n"
            "## 1章 生活\n"
            "本文\n"
            "--- Page 14 ---\n"
            "## 2章 家\n"
            "--- Page 20 ---\n"
            "# 1章・2章 アチーブメントテスト\n"
            "--- Page 22 ---\n"
            "# 1章・2章 クイズ\n"
            "--- Page 24 ---\n"
            "## 3 章料理\n"
            "--- Page 30 ---\n"
            "本文\n"
        )
        rows = extract_curriculum(markdown)

        assert [
            (r["chapter_num"], r["chapter_title"], r["page_start"], r["page_end"])
            for r in rows
        ] == [
            (1, "生活", 8, 13),
            (2, "家", 14, 23),
            (3, "料理", 24, 30),
        ]

    def test_test_and_quiz_headings_not_chapters(self):
        """アチーブメントテスト / クイズ / まとめテスト headings are spans
        across chapters (1章・2章) or reviews — never chapters themselves."""
        markdown = (
            "--- Page 8 ---\n## 1章 生活\n"
            "--- Page 20 ---\n# 1章・2章 クイズ\n"
            "--- Page 22 ---\n# 1章～11章 まとめテスト\n"
            "--- Page 30 ---\n# 2章 復習\n"
        )
        rows = extract_curriculum(markdown)

        assert [r["chapter_num"] for r in rows] == [1]

    def test_repeated_heading_deduped(self):
        """A chapter whose content spans pages repeats its heading — keep the
        first occurrence (its page)."""
        markdown = (
            "--- Page 8 ---\n## 1章 生活\n"
            "--- Page 9 ---\n## 1章 生活\n"
        )
        rows = extract_curriculum(markdown)

        assert len(rows) == 1
        assert rows[0]["page_start"] == 8

    def test_fullwidth_lesson_digits(self):
        markdown = "--- Page 20 ---\n## １課 人・体\n"
        rows = extract_curriculum(markdown)

        assert rows[0]["chapter_num"] == 1
        assert rows[0]["chapter_title"] == "人・体"

    def test_fallback_used_when_toc_finds_nothing(self):
        markdown = (
            "--- Page 1 ---\n前書きです。\n"
            "--- Page 8 ---\n## 1章 生活\n"
            "--- Page 14 ---\n## 2章 家\n"
        )
        rows = extract_curriculum(markdown)

        assert [r["chapter_num"] for r in rows] == [1, 2]

    def test_readable_toc_preferred_over_body_headings(self):
        """A book whose 課 TOC is readable keeps its TOC titles and pages
        even though the body also carries N課 headings. (Both chapters'
        body headings are present, so the cross-check confirms the TOC —
        this is what makes the TOC trustworthy.)"""
        markdown = (
            "--- Page 4 ---\n"
            "第1部 話題別\n"
            "1課 人間関係1：家族と友達、性格 .....20\n"
            "2課 天気 .....76\n"
            "--- Page 20 ---\n## １課にんげん…人間関係1：家族と友達、性格\n"
            "--- Page 76 ---\n## 2課 天気\n"
        )
        rows = extract_curriculum(markdown)

        assert [r["chapter_num"] for r in rows] == [1, 2]
        assert rows[0]["page_start"] == 20  # TOC page, not the body heading page
        assert "人間関係1" in rows[0]["chapter_title"]  # clean TOC title


class TestKorean:
    """Korean textbook TOCs — 부/장/과 markers (registry, no language hint)."""

    def test_lesson_marker(self):
        markdown = "--- Page 4 ---\n1과 인사 .....5\n2과 가족 .....9\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "인사", 5),
            (2, "가족", 9),
        ]

    def test_chapter_marker_body_heading(self):
        markdown = "--- Page 8 ---\n## 1장 서론\n--- Page 12 ---\n## 2장 사회\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "서론", 8),
            (2, "사회", 12),
        ]

    def test_part_marker(self):
        markdown = "--- Page 4 ---\n제1부 인사와 가족\n1과 인사 .....5\n2과 가족 .....9\n"
        rows = extract_curriculum(markdown)

        assert rows[0]["part"].startswith("제1부")
        assert [r["chapter_num"] for r in rows] == [1, 2]


class TestChinese:
    """Chinese textbook TOCs — 部/章/课/单元 markers."""

    def test_simplified_lesson(self):
        markdown = "--- Page 4 ---\n第1课 问候 .....5\n2课 家庭 .....9\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "问候", 5),
            (2, "家庭", 9),
        ]

    def test_unit_body_heading(self):
        markdown = "--- Page 20 ---\n## 1单元 你好\n--- Page 26 ---\n## 2单元 家庭\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "你好", 20),
            (2, "家庭", 26),
        ]


class TestEnglish:
    """English/Latin textbook TOCs — part/chapter/unit/lesson markers."""

    def test_chapter_with_dots(self):
        markdown = "--- Page 4 ---\nChapter 1 Introduction .....5\nChapter 2 The Family .....9\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "Introduction", 5),
            (2, "The Family", 9),
        ]

    def test_part_and_unit(self):
        markdown = (
            "--- Page 4 ---\n"
            "Part I Foundations\n"
            "Unit 1 Greetings .....5\n"
            "Unit 2 Family .....9\n"
        )
        rows = extract_curriculum(markdown)

        assert rows[0]["part"] == "Part I Foundations"
        assert [r["chapter_num"] for r in rows] == [1, 2]


class TestOrderedStyle:
    """Numbered TOCs without dot leaders."""

    def test_marker_with_trailing_page(self):
        markdown = "--- Page 4 ---\nChapter 1 Introduction 5\nChapter 2 The Family 9\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "Introduction", 5),
            (2, "The Family", 9),
        ]

    def test_numbered_prefix_entries(self):
        markdown = "--- Page 4 ---\n1. Introduction 5\n2. The Family 9\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "Introduction", 5),
            (2, "The Family", 9),
        ]

    def test_tiny_trailing_number_is_list_index(self):
        """A trailing number below the page floor (a list index or
        footnote, not a page) is not read as a chapter page."""
        markdown = "--- Page 4 ---\n1. Introduction 2\n2. The Family 5\n"
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (2, "The Family", 5),
        ]


class TestCrossCheck:
    """Content-association cross-check: TOC candidate titles that also
    reappear in the document's body confirm the TOC scan. The signal is
    soft — no chapter is dropped because OCR made its title differ. Gate:
    ≥0.7 trust the TOC; 0.3–0.7 prefer body headings; <0.3 no map (the
    escalation branch is wired by ticket 03)."""

    def test_readable_toc_high_confidence_wins(self):
        markdown = (
            "--- Page 4 ---\n"
            "1課 人間関係 .....20\n"
            "2課 天気 .....76\n"
            "--- Page 20 ---\n"
            "## 1課 人間関係\n本文\n"
            "--- Page 76 ---\n"
            "## 2課 天気\n本文\n"
        )
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "人間関係", 20),
            (2, "天気", 76),
        ]

    def test_title_drift_prefers_body_headings(self):
        """One of two TOC titles fails to reappear (0.5 confidence) — the
        body headings win, with their drifted titles kept, not dropped."""
        markdown = (
            "--- Page 4 ---\n"
            "1課 人間関係 .....20\n"
            "2課 天気 .....76\n"
            "--- Page 20 ---\n"
            "## 1課 にんげん…人間関係\n本文\n"
            "--- Page 76 ---\n"
            "## 2課 てんき\n本文\n"
        )
        rows = extract_curriculum(markdown)

        assert [(r["chapter_num"], r["chapter_title"], r["page_start"]) for r in rows] == [
            (1, "にんげん…人間関係", 20),
            (2, "てんき", 76),
        ]

    def test_low_confidence_yields_empty_map(self):
        """Neither TOC title reappears (<0.3) — no map, so the current
        lesson fallback runs. (The SLM escalation lives in ticket 03.)"""
        markdown = (
            "--- Page 4 ---\n"
            "1課 人間関係 .....20\n"
            "2課 天気 .....76\n"
            "--- Page 20 ---\n"
            "## 別の話題\n本文\n"
            "--- Page 76 ---\n"
            "## また別の話題\n本文\n"
        )
        assert extract_curriculum(markdown) == []

    def test_no_body_pages_trusts_the_scan(self):
        """A document that is only TOC pages (e.g. the golden GOI
        fixture) has no body to refute the scan — the TOC is trusted."""
        markdown = "--- Page 4 ---\n1課 人間関係 .....20\n2課 天気 .....76\n"
        rows = extract_curriculum(markdown)

        assert [r["chapter_num"] for r in rows] == [1, 2]
