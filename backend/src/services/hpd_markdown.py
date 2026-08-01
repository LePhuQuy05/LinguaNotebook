"""HPD markdown → typed content blocks.

HPD's markdown-mode output is plain text: pipe tables (| a | b |, with
| --- | separator rows), heading-like standalone lines (はじめに, ■本書の特徴),
list markers (・, ①-⑳, numbered), and paragraphs. This service recognizes
what HPD actually emits and splits one page's text into typed blocks in
reading order.

Classification is conservative by design: table rows must never split
into separate blocks, and heading-like lines degrade to paragraphs when
unsure. Every non-blank line is preserved exactly once, in order.
"""

import re
from dataclasses import dataclass

BLOCK_HEADER = "header"
BLOCK_TABLE = "table"
BLOCK_LIST = "list"
BLOCK_PARAGRAPH = "paragraph"

# Kana + kanji (for heading detection)
_KANA_KANJI = re.compile(r"[぀-ヿ一-鿿]")
# Digit/punctuation-only lines (page numbers like "166") are never headings
_NON_TEXT_ONLY = re.compile(r"^[\d\s.·•\-–—:：,，;；()（）*]+$")
# List item markers: bullets, circled numbers, numbered items
_LIST_RE = re.compile(r"^(・|•|\*|-|\d+[.、]\s?|[①-⑳])")
# Section markers that signal a heading even without kana/kanji
_SECTION_MARKERS = ("■", "●", "▲", "◆")
_SENTENCE_ENDINGS = ("。", "．", "!", "？", "?", ".")
_MAX_HEADER_LEN = 60


@dataclass(frozen=True)
class Block:
    """A typed content block from one page's markdown."""

    block_type: str
    content: str
    bbox: None = None


def _collect_table(lines: list[str], start: int) -> tuple[str, int]:
    """Collect a table block starting at a '|' line.

    HPD separates table rows with blank lines (real output does this), so
    interior blanks are absorbed while the next non-blank line is still a
    table row. A blank followed by a non-table line ends the table.
    """
    collected: list[str] = []
    j = start
    n = len(lines)
    while j < n:
        stripped = lines[j].strip()
        if stripped.startswith("|"):
            collected.append(stripped)
            j += 1
        elif stripped == "":
            k = j
            while k < n and lines[k].strip() == "":
                k += 1
            if k < n and lines[k].strip().startswith("|"):
                j = k  # blank line inside the table — absorb and continue
            else:
                break
        else:
            break
    return "\n".join(collected), j


def _is_header_line(line: str, prev_blank: bool, next_blank: bool) -> bool:
    """Is this line a heading?

    A heading must be standalone (bounded by blank lines), short, not end
    with sentence punctuation, and contain kana/kanji (or a section marker).
    Purely numeric lines (page numbers) and long prose are not headings.
    """
    s = line.strip()
    if not s or len(s) > _MAX_HEADER_LEN:
        return False
    if not (prev_blank and next_blank):
        return False
    if s.startswith("|"):
        return False
    if s.endswith(_SENTENCE_ENDINGS):
        return False
    if _NON_TEXT_ONLY.match(s):
        return False
    if s.startswith(_SECTION_MARKERS):
        return True
    if s.endswith(("：", ":")):
        return True
    return bool(_KANA_KANJI.search(s))


def _collect_list(lines: list[str], start: int) -> tuple[str, int]:
    """Collect consecutive list-item lines into one list block."""
    collected = [lines[start].strip()]
    j = start + 1
    n = len(lines)
    while j < n and _LIST_RE.match(lines[j].strip()):
        collected.append(lines[j].strip())
        j += 1
    return "\n".join(collected), j


def parse_page_blocks(page_text: str) -> list[Block]:
    """Convert one page of HPD markdown output into typed blocks.

    Args:
        page_text: the text of a single page (without the `--- Page N ---`
            marker — the worker splits pages before calling this).

    Returns:
        Typed blocks in reading order. Every non-blank line appears exactly
        once across the blocks; blank lines separate blocks.
    """
    lines = page_text.split("\n")
    n = len(lines)
    blocks: list[Block] = []
    i = 0

    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        # Table: any line starting with '|'
        if s.startswith("|"):
            content, j = _collect_table(lines, i)
            blocks.append(Block(block_type=BLOCK_TABLE, content=content))
            i = j
            continue

        # List: item markers
        if _LIST_RE.match(s):
            content, j = _collect_list(lines, i)
            blocks.append(Block(block_type=BLOCK_LIST, content=content))
            i = j
            continue

        # Heading: standalone short line
        prev_blank = i == 0 or lines[i - 1].strip() == ""
        next_blank = i == n - 1 or lines[i + 1].strip() == ""
        if _is_header_line(s, prev_blank, next_blank):
            blocks.append(Block(block_type=BLOCK_HEADER, content=s))
            i += 1
            continue

        # Paragraph: accumulate consecutive non-blank non-special lines.
        # A heading cannot start a paragraph run mid-flow: it needs blank
        # lines on both sides, so a non-blank neighbour means it's prose.
        collected = [s]
        j = i + 1
        while j < n:
            t = lines[j].strip()
            if not t:
                break
            if t.startswith("|") or _LIST_RE.match(t):
                break
            collected.append(t)
            j += 1
        blocks.append(Block(block_type=BLOCK_PARAGRAPH, content="\n".join(collected)))
        i = j

    return blocks


def split_pages(markdown: str) -> list[tuple[int, str]]:
    """Split combined markdown into (page_number, page_body) pairs.

    The `--- Page N ---` marker format is the single source of truth for
    page attribution — shared by the worker and the CLI demo.
    """
    parts = re.split(r"--- Page (\d+) ---", markdown)
    return [
        (int(parts[i]), parts[i + 1])
        for i in range(1, len(parts), 2)
    ]


def main() -> None:
    """CLI demo: `python -m src.services.hpd_markdown <file.md>`."""
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python -m src.services.hpd_markdown <file.md>")
        sys.exit(1)

    raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    pages = split_pages(raw)
    if not pages:
        pages = [(1, raw)]
    for page_num, body in pages:
        print(f"### Page {page_num} ###")
        for b in parse_page_blocks(body):
            preview = b.content.replace("\n", " ⏎ ")
            print(f"  [{b.block_type}] {preview[:120]}")
        print()


if __name__ == "__main__":
    main()
