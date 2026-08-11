"""SmartChunker tests — structure-aware chunking with page metadata.

Page numbers must flow from the ContentBlock rows into each chunk's
metadata (page_start/page_end), so Qdrant payloads can cite real pages
and lessons can filter by page range.
"""

from src.utils.chunker import SmartChunker


def _block(bid, btype, content, page):
    return {
        "id": bid,
        "block_type": btype,
        "content_markdown": content,
        "page_number": page,
    }


class TestPageMetadata:
    def test_structural_block_carries_its_page(self):
        chunks = SmartChunker().chunk_blocks([_block("b1", "header", "はじめに", 3)])

        assert chunks[0].metadata["page_start"] == 3
        assert chunks[0].metadata["page_end"] == 3

    def test_merged_paragraph_chunk_covers_min_max_pages(self):
        blocks = [
            _block("b1", "paragraph", "文1。", 4),
            _block("b2", "paragraph", "文2。", 5),
        ]

        chunks = SmartChunker().chunk_blocks(blocks)

        merged = chunks[0]
        assert merged.block_type == "paragraph"
        assert merged.metadata["page_start"] == 4
        assert merged.metadata["page_end"] == 5

    def test_blocks_without_page_number_default_to_page_1(self):
        blocks = [{"id": "b1", "block_type": "list", "content_markdown": "・x"}]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert chunks[0].metadata["page_start"] == 1
        assert chunks[0].metadata["page_end"] == 1


class TestChunkingBehaviour:
    def test_headers_lists_tables_stay_intact(self):
        blocks = [
            _block("b1", "header", "章題", 1),
            _block("b2", "list", "・a\n・b", 1),
            _block("b3", "table", "| a |", 1),
        ]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert [c.block_type for c in chunks] == ["header", "list", "table"]

    def test_consecutive_paragraphs_merge_into_one_chunk(self):
        blocks = [
            _block(f"b{i}", "paragraph", "これは日本語のテストの文章です。", 1)
            for i in range(4)
        ]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert len(chunks) == 1
        assert chunks[0].metadata["block_count"] == 4

    def test_japanese_paragraph_runs_split_at_the_token_cap(self):
        """Regression: the old word-only estimate (~1 token per Japanese
        block) never hit the 500-token cap, so runs grew unbounded. CJK
        chars now count (~1 token / 1.8 chars), so long runs split."""
        # 450 CJK chars ≈ 250 tokens per block; 3 blocks ≈ 750 > 500
        blocks = [
            _block(f"b{i}", "paragraph", "日本語の文章です。" * 50, 1)
            for i in range(3)
        ]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert len(chunks) == 2
        # 1-sentence overlap: the last block of chunk 0 also opens chunk 1
        assert chunks[0].metadata["block_count"] == 2
        assert chunks[1].metadata["block_count"] == 2
        assert chunks[0].source_block_ids[-1] == chunks[1].source_block_ids[0]

    def test_structural_block_flushes_pending_paragraphs(self):
        blocks = [
            _block("b1", "paragraph", "本文です。", 1),
            _block("b2", "list", "・項目", 1),
        ]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert [c.block_type for c in chunks] == ["paragraph", "list"]

    def test_source_block_ids_preserved(self):
        blocks = [_block("b1", "paragraph", "文1。", 1), _block("b2", "paragraph", "文2。", 1)]

        chunks = SmartChunker().chunk_blocks(blocks)

        assert chunks[0].source_block_ids == ["b1", "b2"]
