"""Curriculum map extraction — parts/chapters from a textbook's TOC.

Rule-based and conservative by design (no LLM; an optional small-LM
escalation is layered on top of this in the parse pipeline). Scans the
parsed markdown page by page for:

- part headers: lines carrying a part marker (第N部 / 제N부 / Part N)
- chapter entries: lines carrying a structural marker from the
  language-agnostic registry — 課/课/章/장/과/単元/단원/单元 for CJK,
  Chapter/Unit/Lesson for Latin — with a dotted page number
  (``.....N``) on the same or the next two lines, or a no-dot trailing
  page (Ordered style: ``Chapter 1 Intro 5``, ``1. Intro 5``)

The registry is merged across languages, so detection never depends on
knowing the document's language; when a language is known it only
selects the practice-section stoplist (まとめ/復習 vs Appendix/Index).

When that TOC scan finds no chapters — a book structured as ``N章`` body
headings, or a TOC whose dotted anchors the OCR mangled — extraction
falls back to body headings (``## N章 <topic>``), which carry the
authoritative start page.

Chapter page ranges come from consecutive chapter pages (never array
indexes). Entries that are practice/mock sections are skipped so ranges
bridge them. Unknown structure → empty map; lessons fall back to
current behaviour.

Real output note (GOI.pdf, 2026-08-11): the OCR mismerges the 第2部
header into a chapter line ("32課 第2部...") — a chapter whose topic
starts with 第N部 is treated as a part boundary instead.
"""

import re
from dataclasses import dataclass
from typing import TypedDict

from src.services.hpd_markdown import split_pages

LEVEL_PART = "part"
LEVEL_CHAPTER = "chapter"
LEVEL_UNIT = "unit"
LEVEL_LESSON = "lesson"


class Entry(TypedDict):
    """A single extracted chapter row before page ranges are resolved."""

    part: str
    chapter_num: int
    chapter_title: str
    page: int


class ChapterRow(TypedDict):
    """A resolved curriculum-map row (page range computed from neighbours)."""

    part: str
    chapter_num: int
    chapter_title: str
    page_start: int
    page_end: int


@dataclass(frozen=True)
class Marker:
    """A structural marker (課/章/unit/…) with the level it denotes."""

    text: str
    level: str


# Language-agnostic structural-marker registry. CJK markers are shared
# across languages — 部/章/課 appear in both Japanese and Chinese, and
# Korean 부/장/과 are the same Hanja — so one merged registry covers
# detection without ever needing to know the document's language.
_MARKERS: tuple[Marker, ...] = (
    Marker("部", LEVEL_PART),
    Marker("부", LEVEL_PART),
    Marker("Part", LEVEL_PART),
    Marker("章", LEVEL_CHAPTER),
    Marker("장", LEVEL_CHAPTER),
    Marker("Chapter", LEVEL_CHAPTER),
    Marker("単元", LEVEL_UNIT),
    Marker("단원", LEVEL_UNIT),
    Marker("单元", LEVEL_UNIT),
    Marker("Unit", LEVEL_UNIT),
    Marker("課", LEVEL_LESSON),
    Marker("课", LEVEL_LESSON),
    Marker("과", LEVEL_LESSON),
    Marker("Lesson", LEVEL_LESSON),
)

_CJK_MARKERS = "課|课|章|장|과|単元|단원|单元"
_EN_MARKERS = "Chapter|Unit|Lesson"

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

# CJK entry: [第|제]N<marker> <topic> [....page] — the dotted page may
# sit on a later line (the OCR often breaks it across the line).
_CJK_ENTRY_RE = re.compile(
    rf"^\s*(?:第|제)?(\d{{1,2}})\s*(?:{_CJK_MARKERS})\s*(.+?)\s*(?:\.{{3,}}.*)?$"
)
# Latin entry: <marker> N <topic> [....page]
_EN_ENTRY_RE = re.compile(
    rf"^\s*(?:{_EN_MARKERS})\s+(\d{{1,2}})\s+(.+?)\s*(?:\.{{3,}}.*)?$"
)
# Latin entry with a no-dot trailing page: "Chapter 1 Introduction 5"
_EN_TRAILING_RE = re.compile(
    rf"^\s*(?:{_EN_MARKERS})\s+(\d{{1,2}})\s+(.+?)\s+(\d{{1,3}})\s*$"
)
# Ordered style, no-dot trailing page: "1. Introduction 5"
_NUM_PREFIX_RE = re.compile(r"^\s*(\d{1,2})\.\s+(.+?)\s+(\d{1,3})\s*$")

# Part headers
_PART_RE = re.compile(r"(?:第|제)?(\d+)(?:部|부)")
_EN_PART_RE = re.compile(r"^\s*Part\s+([IVXL\d]+)\s+(.+?)\s*(?:\.{3,}.*)?$")

_PAGE_DOTS_RE = re.compile(r"\.{3,}\s*(\d{1,3})")

# Body-heading chapters (## N章 <topic> / # Chapter N <topic>)
_BODY_CJK_RE = re.compile(
    rf"^\s*#{{1,3}}\s*(?:第|제)?(\d{{1,2}})\s*(?:{_CJK_MARKERS})\s*(.+?)\s*$"
)
_BODY_EN_RE = re.compile(
    rf"^\s*#{{1,3}}\s*(?:{_EN_MARKERS})\s+(\d{{1,2}})\s+(.+?)\s*$"
)


# Practice/mock/test/review sections that are not chapters, per language.
_STOPLIST_BY_LANGUAGE: dict[str, str] = {
    "ja": r"第\d+回|実力|模擬|索引|別冊|テスト|クイズ|まとめ|復習",
    "ko": r"연습|모의|평가|색인|정답",
    "zh": r"练习|模拟|测试|索引|答案|复习|测验",
    "en": r"Appendix|Preface|Index|Answer|Glossary|Review|Quiz|Test|Summary",
}
_DEFAULT_STOPLIST = re.compile("|".join(_STOPLIST_BY_LANGUAGE.values()))


def _stoplist(language: str | None) -> re.Pattern[str]:
    """The practice-section stoplist for a language (merged when unknown)."""
    if language:
        key = language.lower()[:2]
        if key in _STOPLIST_BY_LANGUAGE:
            return re.compile(_STOPLIST_BY_LANGUAGE[key])
    return _DEFAULT_STOPLIST


def _match_entry(line: str) -> tuple[int, str, int | None] | None:
    """Return ``(chapter_num, topic, page)`` when line is a chapter entry.

    ``page`` is set only for no-dot Ordered-style entries whose trailing
    number is the page; dotted entries resolve their page by probing
    nearby lines instead. None when the line is not an entry.
    """
    m = _EN_TRAILING_RE.match(line)
    if m:
        return int(m.group(1)), m.group(2).strip(), int(m.group(3))
    m = _NUM_PREFIX_RE.match(line)
    if m:
        page = int(m.group(3))
        # A trailing number only reads as a page when it is plausibly one;
        # tiny values are usually list indices, not pages.
        if page >= 3:
            return int(m.group(1)), m.group(2).strip(), page
        return None
    m = _EN_ENTRY_RE.match(line)
    if m:
        return int(m.group(1)), m.group(2).strip(), None
    m = _CJK_ENTRY_RE.match(line)
    if m:
        return int(m.group(1)), m.group(2).strip(), None
    return None


def _extract_entries(markdown: str, language: str | None = None) -> list[Entry]:
    """Scan every page for part headers and chapter entries."""
    entries: list[Entry] = []
    current_part = ""
    stop = _stoplist(language)
    for page_num, body in split_pages(markdown):
        lines = body.split("\n")
        for idx, line in enumerate(lines):
            entry = _match_entry(line)
            if entry is None:
                # Not a chapter entry — maybe a part header. A standalone
                # part line must not carry a lesson marker (the OCR merges
                # "32課 第2部 …" into a chapter line, handled below).
                if _EN_PART_RE.match(line) or (
                    _PART_RE.search(line) and "課" not in line[:8]
                ):
                    current_part = line.strip()[:200]
                continue

            num, topic, inline_page = entry
            if stop.search(topic):
                continue
            if _PART_RE.search(topic) and "部" in topic[:6]:
                # "32課 第2部 性質別…" — the part header was absorbed into
                # a chapter line: treat as a boundary.
                current_part = topic[:200]
                continue
            if _EN_PART_RE.match(topic):
                current_part = topic[:200]
                continue

            page = inline_page
            if page is None:
                # Dotted ".....N" on this line or the next two.
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


def _extract_body_chapters(markdown: str, language: str | None = None) -> list[Entry]:
    """Chapters from body headings (``## N章 <title>`` / ``# Chapter N …``).

    Fallback for books whose TOC layout the dotted-anchor scan can't
    read — e.g. the Shinkanzen N3 Kanji book, whose TOC pages break the
    page anchors across lines. A body heading carries the page the
    chapter actually starts on, which is more reliable. Headings that
    are tests/quizzes or span several chapters (``1章・2章``) are
    skipped; a chapter whose heading repeats (content spanning pages) is
    kept once, at its first page.
    """
    entries: list[Entry] = []
    seen: set[int] = set()
    stop = _stoplist(language)
    for page_num, body in split_pages(markdown):
        for line in body.split("\n"):
            match = _BODY_CJK_RE.match(line.translate(_FULLWIDTH_DIGITS))
            if not match:
                match = _BODY_EN_RE.match(line)
            if not match:
                continue
            num = int(match.group(1))
            topic = match.group(2).strip()
            # A heading spanning chapters ("1章・2章 クイズ") carries
            # another marker in its topic; a heading whose topic starts
            # with a digit continues a span ("Chapter 1-3 Review"). The
            # title itself may legitimately contain ・ (人・体).
            if stop.search(topic) or "章" in topic or "課" in topic:
                continue
            if re.match(r"^\d", topic):
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


def extract_curriculum(markdown: str, language: str | None = None) -> list[ChapterRow]:
    """Extract the curriculum map from a book's parsed markdown.

    ``language`` (optional) narrows the practice-section stoplist only;
    chapter detection itself is language-agnostic via the merged marker
    registry.

    Returns rows in reading order: {part, chapter_num, chapter_title,
    page_start, page_end}. Page ranges are resolved from consecutive
    chapter pages; the final chapter extends to the document's last
    page. Empty list when no chapters are found (conservative).

    The TOC dotted-anchor scan handles 課-based TOCs (GOI); when it
    finds nothing the extraction falls back to body headings (章-based
    books like the N3 Kanji book, or any TOC the OCR mangled).
    """
    entries = [e for e in _extract_entries(markdown, language) if e["page"]]
    if not entries:
        entries = _extract_body_chapters(markdown, language)
    if not entries:
        return []

    entries.sort(key=lambda e: e["page"])
    last_page = max(n for n, _ in split_pages(markdown)) if split_pages(markdown) else None

    rows: list[ChapterRow] = []
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
