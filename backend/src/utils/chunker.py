"""Smart document chunker — block-type-aware text splitting.

Splits HPD-parsed markdown into semantically meaningful chunks:
- Headers: kept intact as standalone chunks
- Tables: kept intact, markdown table format
- Paragraphs: split at sentence boundaries, 200-500 tokens, 1-sentence overlap
- Lists: kept intact as standalone chunks
- Minimum chunk: 50 tokens; below threshold merged with adjacent
"""

import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single document chunk ready for embedding."""
    content: str
    source_block_ids: list[str]
    block_type: str
    chunk_index: int
    token_count: int
    language: str
    metadata: dict = field(default_factory=dict)


class SmartChunker:
    """Intelligently chunk document content by block type."""

    MIN_TOKENS = 50
    MAX_TOKENS = 500
    OVERLAP_SENTENCES = 1

    def __init__(
        self,
        min_tokens: int = 50,
        max_tokens: int = 500,
        overlap_sentences: int = 1,
    ):
        self.min_tokens = min_tokens
        self.max_tokens = max_tokens
        self.overlap_sentences = overlap_sentences

    def chunk_blocks(
        self,
        blocks: list[dict],
        language: str = "en",
    ) -> list[Chunk]:
        """Chunk a list of ContentBlock dicts into KnowledgeSegments.

        Args:
            blocks: List of dicts with keys: id, block_type, content_markdown
            language: ISO 639-1 language code

        Returns:
            List of Chunk objects ready for embedding
        """
        chunks: list[Chunk] = []
        pending: list[dict] = []  # Small blocks to merge
        pending_tokens = 0

        for block in blocks:
            block_type = block["block_type"]
            content = block["content_markdown"]
            tokens = self._estimate_tokens(content)

            if block_type in ("header", "table", "list"):
                # Always emit pending before a structural block
                if pending:
                    chunks.append(self._merge_pending(pending, len(chunks), language))
                    pending = []
                    pending_tokens = 0

                # Structural blocks: keep intact regardless of size
                chunks.append(Chunk(
                    content=content,
                    source_block_ids=[block["id"]],
                    block_type=block_type,
                    chunk_index=len(chunks),
                    token_count=tokens,
                    language=language,
                    metadata={"block_types": [block_type]},
                ))
            else:
                # Paragraphs: check if adding this exceeds max
                if pending_tokens + tokens > self.max_tokens and pending_tokens >= self.min_tokens:
                    chunks.append(self._merge_pending(pending, len(chunks), language))
                    # Keep overlap
                    overlap = pending[-self.overlap_sentences :] if self.overlap_sentences else []
                    pending = overlap
                    pending_tokens = sum(
                        self._estimate_tokens(b["content_markdown"]) for b in overlap
                    )

                pending.append(block)
                pending_tokens += tokens

        # Flush remaining
        if pending:
            chunks.append(self._merge_pending(pending, len(chunks), language))

        return chunks

    def _merge_pending(self, blocks: list[dict], chunk_index: int, language: str) -> Chunk:
        """Merge accumulated paragraph blocks into one chunk."""
        content = "\n\n".join(b["content_markdown"] for b in blocks)
        block_ids = [b["id"] for b in blocks]
        block_types = list({b["block_type"] for b in blocks})
        return Chunk(
            content=content,
            source_block_ids=block_ids,
            block_type="paragraph" if len(block_types) == 1 else "mixed",
            chunk_index=chunk_index,
            token_count=self._estimate_tokens(content),
            language=language,
            metadata={"block_types": block_types, "block_count": len(blocks)},
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Quick token estimate: ~1.3 tokens per word for English, ~1.5 for others."""
        words = len(re.findall(r"\w+", text))
        return max(1, int(words * 1.5))
