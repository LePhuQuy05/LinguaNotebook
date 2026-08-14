"""Curriculum map extraction — parts/chapters from a textbook's TOC.

Rule-based and conservative by design (no LLM). Scans the parsed
markdown page by page for:

- part headers: lines containing ``第N部`` (e.g. 第1部 話題別に言葉を学ぼう)
- chapter entries: lines matching ``N課<topic>`` with a dotted page
  number (``.....N``) on the same or the next two lines

When that TOC scan finds no 課-based chapters — a book structured as
``N章`` (e.g. the Shinkanzen N3 Kanji book), or a TOC whose dotted
anchors the OCR mangled — extraction falls back to body headings
(``## N章 <topic>``), which carry the authoritative start page.

Chapter page ranges come from consecutive chapter pages (never array
indexes). Entries that are practice/mock sections (実力を試そう, 第N回,
模擬試験) are skipped so ranges bridge them. Unknown structure → empty
map; lessons fall back to current behaviour.

Real output note (GOI.pdf, 2026-08-11): the OCR mismerges the 第2部
header into a chapter line ("32課 第2部 性質別...") — a chapter whose
topic starts with 第N部 is treated as a part boundary instead.
"""

import re

from src.services.hpd_markdown import split_pages

_PART_RE = re.compile(r"第(\d+)部")
_CHAPTER_RE = re.compile(r"^\s*(\d{1,2})\s*[課课]\s*(.+?)\s*$")
_PAGE_DOTS_RE = re.compile(r"\.{3,}\s*(\d{1,3})")
# Topics that are practice/mock/test/review sections, not chapters
_NON_CHAPTER = re.compile(r"第\d+回|実力|模擬|索引|別冊|テスト|クイズ|まとめ|復習")
# Body-heading chapter (## 3章 家 / ## 3 章料理 / ## １課 人・体): the number
# may be full-width and the OCR may glue/split spaces around the marker.
_BODY_CHAPTER_RE = re.compile(r"^\s*#{1,3}\s*(\d{1,2})\s*[課课章]\s*(.+?)\s*$")
_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


def _extract_entries(markdown: str) -> list[dict]:
    """Scan every page for part headers and chapter entries."""
    entries: list[dict] = []
    current_part = ""
    for page_num, body in split_pages(markdown):
        lines = body.split("\n")
        for idx, line in enumerate(lines):
            part_match = _PART_RE.search(line)
            if part_match and "課" not in line[:8]:
                # A standalone part header (第1部 話題別...) — not absorbed
                # into a chapter line. Note: OCR sometimes merges them into
                # a chapter line ("32課 第2部 ...") — handled below.
                current_part = line.strip()[:200]
                continue

            chapter_match = _CHAPTER_RE.match(line)
            if not chapter_match:
                continue
            num = int(chapter_match.group(1))
            topic = chapter_match.group(2)

            if _PART_RE.search(topic) and "部" in topic[:6]:
                # "32課 第2部 性質別に言葉を学ぼう" — the part header was
                # absorbed into the chapter line: treat as a boundary.
                current_part = topic[:200]
                continue
            if _NON_CHAPTER.search(topic):
                continue

            # Page number: dotted ".....N" on this line or the next two.
            page = None
            for probe in lines[idx : idx + 3]:
                m = _PAGE_DOTS_RE.search(probe)
                if m:
                    page = int(m.group(1))
                    break
            if page is None:
                continue  # conservative: unresolvable page → drop entry

            entries.append({
                "part": current_part,
                "chapter_num": num,
                "chapter_title": topic[:500],
                "page": page,
            })
    return entries


def _extract_body_chapters(markdown: str) -> list[dict]:
    """Chapters from body headings (``## N章 <title>`` / ``## N課 <title>``).

    Fallback for books whose TOC layout the dotted-anchor scan can't
    read — e.g. the Shinkanzen N3 Kanji book, whose TOC pages break the
    page anchors across lines. A body heading carries the page the
    chapter actually starts on, which is more reliable. Headings that are
    tests/quizzes (アチーブメントテスト, クイズ, まとめテスト) or span
    several chapters (``1章・2章``) are skipped; a chapter whose heading
    repeats (content spanning pages) is kept once, at its first page.
    """
    entries: list[dict] = []
    seen: set[int] = set()
    for page_num, body in split_pages(markdown):
        for line in body.split("\n"):
            match = _BODY_CHAPTER_RE.match(line.translate(_FULLWIDTH_DIGITS))
            if not match:
                continue
            num = int(match.group(1))
            topic = match.group(2).strip()
            # A heading spanning chapters ("1章・2章 クイズ") carries another
            # chapter marker in its topic; the title itself may legitimately
            # contain ・ (人・体), so only the 章/課 presence disqualifies.
            if _NON_CHAPTER.search(topic) or "章" in topic or "課" in topic:
                continue
            if num in seen:
                continue
            seen.add(num)
            entries.append({
                "part": "",
                "chapter_num": num,
                "chapter_title": topic[:200],
                "page": page_num,
            })
    return entries


def extract_curriculum(markdown: str) -> list[dict]:
    """Extract the curriculum map from a book's parsed markdown.

    Returns rows in reading order: {part, chapter_num, chapter_title,
    page_start, page_end}. Page ranges are resolved from consecutive
    chapter pages; the final chapter extends to the document's last
    page. Empty list when no chapters are found (conservative).

    The TOC dotted-anchor scan handles 課-based TOCs (GOI); when it
    finds nothing the extraction falls back to body headings (章-based
    books like the N3 Kanji book, or any TOC the OCR mangled).
    """
    entries = [e for e in _extract_entries(markdown) if e["page"]]
    if not entries:
        entries = _extract_body_chapters(markdown)
    if not entries:
        return []

    entries.sort(key=lambda e: e["page"])
    last_page = max(n for n, _ in split_pages(markdown)) if split_pages(markdown) else None

    rows = []
    for i, entry in enumerate(entries):
        page_end = (
            entries[i + 1]["page"] - 1 if i + 1 < len(entries) else (last_page or entry["page"])
        )
        rows.append({
            "part": entry["part"],
            "chapter_num": entry["chapter_num"],
            "chapter_title": entry["chapter_title"],
            "page_start": entry["page"],
            "page_end": max(page_end, entry["page"]),
        })
    return rows
