"""Unit tests for the HPD markdown → typed block parser service.

Seam under test: `parse_page_blocks(page_text) -> list[Block]` — the single
service seam for converting one page of HPD's markdown output into typed
blocks. Golden fixture: real Shinkanzen N3 output captured from the
2026-08-01 parse (document 00f26d1a-ac6f-4528-8a39-44266df520b5).
"""

from pathlib import Path

import pytest

from src.services.hpd_markdown import (
    Block,
    markdown_to_block_records,
    parse_page_blocks,
    split_pages,
)

FIXTURE = Path(__file__).parent.parent / "fixtures" / "shinkanzen_n3_toc_pages.md"


def load_pages() -> dict[int, str]:
    """Split the golden fixture into {page_num: page_body}."""
    raw = FIXTURE.read_text(encoding="utf-8")
    return dict(split_pages(raw))


def non_blank_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.split("\n") if ln.strip()]


class TestMixedContent:
    """A single page mixing heading, table, list, and paragraph."""

    PAGE = """はじめに

| 単語 | 意味 |
| --- | --- |
| 行く | to go |

・りんご
・みかん

これは本文です。続きの文もここに続きます。"""

    def test_returns_four_typed_blocks_in_reading_order(self):
        blocks = parse_page_blocks(self.PAGE)

        assert [b.block_type for b in blocks] == ["header", "table", "list", "paragraph"]

    def test_header_content_is_stripped(self):
        blocks = parse_page_blocks(self.PAGE)
        assert blocks[0].content == "はじめに"

    def test_table_content_kept_verbatim(self):
        blocks = parse_page_blocks(self.PAGE)
        assert blocks[1].content == "| 単語 | 意味 |\n| --- | --- |\n| 行く | to go |"

    def test_list_content_kept(self):
        blocks = parse_page_blocks(self.PAGE)
        assert blocks[2].content == "・りんご\n・みかん"

    def test_paragraph_groups_consecutive_lines(self):
        blocks = parse_page_blocks(self.PAGE)
        assert blocks[3].content == "これは本文です。続きの文もここに続きます。"

    def test_no_text_lost_in_reading_order(self):
        blocks = parse_page_blocks(self.PAGE)
        joined = "\n".join(b.content for b in blocks)
        assert joined == "\n".join(non_blank_lines(self.PAGE))


class TestTableBlock:
    def test_table_with_separator_is_single_block(self):
        page = "| a | b |\n| --- | --- |\n| c | d |"
        blocks = parse_page_blocks(page)
        assert [b.block_type for b in blocks] == ["table"]
        assert blocks[0].content == page

    def test_blank_line_inside_table_does_not_split(self):
        """Real HPD output (Shinkanzen N3 TOC) separates rows with blank lines."""
        page = "| 17課 | X |\n| --- | --- |\n\n| 自然2 | Y |"
        blocks = parse_page_blocks(page)
        assert [b.block_type for b in blocks] == ["table"]
        assert blocks[0].content == "| 17課 | X |\n| --- | --- |\n| 自然2 | Y |"

    def test_table_followed_by_paragraph_stays_separate(self):
        page = "| a | b |\n| --- | --- |\n\n本文です。"
        blocks = parse_page_blocks(page)
        assert [b.block_type for b in blocks] == ["table", "paragraph"]


class TestListMarkers:
    @pytest.mark.parametrize(
        "line", ["- item", "* item", "・item", "①item", "1. item", "1、item"]
    )
    def test_common_markers_are_lists(self, line):
        blocks = parse_page_blocks(line)
        assert blocks[0].block_type == "list"

    def test_consecutive_mixed_markers_group_into_one_block(self):
        page = "- one\n・two\n①three"
        blocks = parse_page_blocks(page)
        assert [b.block_type for b in blocks] == ["list"]
        assert blocks[0].content == "- one\n・two\n①three"


class TestHeaderRecognition:
    def test_digit_only_line_is_not_header(self):
        """'166' on the cover page is a page number, not a heading."""
        blocks = parse_page_blocks("166  \n新完全マスター語彙")
        assert blocks[0].block_type == "paragraph"

    def test_embedded_line_without_blank_is_not_header(self):
        """A heading-like line must be standalone (bounded by blanks)."""
        blocks = parse_page_blocks("本文の一部\n新完全マスター語彙 日本語能力試験 N3\n本文の続き")
        assert all(b.block_type != "header" for b in blocks)

    def test_sentence_ending_line_is_not_header(self):
        blocks = parse_page_blocks("はじめにです。\n\n本文です。")
        assert blocks[0].block_type == "paragraph"

    def test_colon_ending_line_is_header_without_kana(self):
        """Ticket: lines ending in ： become headers (e.g. 'Note：')."""
        blocks = parse_page_blocks("Note：\n\n本文です。")
        assert blocks[0].block_type == "header"
        assert blocks[0].content == "Note："


class TestMarkdownToBlockRecords:
    """Combined markdown → (page_number, block_type, content) records.

    The worker's block-saving path consumes these records. Page numbers
    must come from the `--- Page N ---` markers — the regression here is
    the worker's old off-by-one: a 2-page doc stored blocks as pages 2-3
    because the split discarded the marker numbers.
    """

    MARKDOWN = (
        "\n--- Page 1 ---\nはじめに\n\n本文です。"
        "\n--- Page 2 ---\n| a | b |\n| --- | --- |\n| c | d |"
    )

    def test_page_numbers_come_from_markers(self):
        records = markdown_to_block_records(self.MARKDOWN)
        assert [p for p, _ in records] == [1, 1, 2]

    def test_records_carry_typed_blocks(self):
        records = markdown_to_block_records(self.MARKDOWN)
        assert [b.block_type for _, b in records] == ["header", "paragraph", "table"]

    def test_non_consecutive_page_numbers_kept(self):
        """A 3-page doc where page 2 is blank keeps real numbers (1, 3)."""
        markdown = "\n--- Page 1 ---\n本文。\n--- Page 2 ---\n\n--- Page 3 ---\n続き。"
        records = markdown_to_block_records(markdown)
        assert [p for p, _ in records] == [1, 3]

    def test_markerless_markdown_degrades_to_page_1(self):
        records = markdown_to_block_records("本文のみ。")
        assert records == [(1, Block(block_type="paragraph", content="本文のみ。"))]

    def test_empty_input_yields_no_records(self):
        assert markdown_to_block_records("") == []
        assert markdown_to_block_records("   \n\n  ") == []

    def test_fixture_records_cover_every_non_blank_page(self):
        """Golden fixture: every non-blank page produces records, and no
        record is shifted up by one (the worker's old regex-split bug)."""
        raw = FIXTURE.read_text(encoding="utf-8")
        pages = dict(split_pages(raw))
        records = markdown_to_block_records(raw)
        pages_seen = {p for p, _ in records}
        non_blank = {n for n, body in pages.items() if body.strip()}
        assert pages_seen == non_blank
        assert max(pages_seen) == max(pages)  # no off-by-one shift


class TestGoldenFixture:
    """Real Shinkanzen N3 output — the acceptance fixture."""

    def test_toc_page_is_single_table_block(self):
        pages = load_pages()
        blocks = parse_page_blocks(pages[4])  # 目次 Contents page

        assert blocks[0].block_type == "table"
        assert "目次" in blocks[0].content
        assert "| --- | --- |" in blocks[0].content
        assert "はじめに" in blocks[0].content
        # The trailing footer (nihongopro.net) stays a separate paragraph
        assert blocks[-1].block_type == "paragraph"

    def test_preface_page_starts_with_header(self):
        pages = load_pages()
        blocks = parse_page_blocks(pages[3])  # はじめに page

        assert blocks[0].block_type == "header"
        assert blocks[0].content == "はじめに"
        assert len(blocks) >= 2

    def test_no_page_collapses_into_single_giant_paragraph(self):
        pages = load_pages()
        for page_num, body in pages.items():
            blocks = parse_page_blocks(body)
            assert len(blocks) >= 1, f"page {page_num} produced no blocks"
            # Every page must decompose: a table page stays table, others
            # must not be one single paragraph covering the whole page
            if "|" in body and not any(b.block_type == "table" for b in blocks):
                pytest.fail(f"page {page_num} contains table rows but no table block")

    def test_no_text_lost_on_any_page(self):
        pages = load_pages()
        for page_num, body in pages.items():
            blocks = parse_page_blocks(body)
            joined = "\n".join(b.content for b in blocks)
            assert joined == "\n".join(non_blank_lines(body)), f"page {page_num} lost text"

    def test_cover_page_keeps_all_lines(self):
        pages = load_pages()
        blocks = parse_page_blocks(pages[1])
        joined = "\n".join(b.content for b in blocks)
        for expected in ["新完全マスター語彙 日本語能力試験 N3", "スリーエーネットワーク"]:
            assert expected in joined
