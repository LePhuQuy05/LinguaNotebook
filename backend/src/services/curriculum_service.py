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

The last fallback is for workbooks whose lessons are numbered but carry
no marker at all — listening/grammar books (``## 2 ポイント理解``,
``## 1 -A 間違えやすい音``). It requires at least three numbered
headings and excludes answer-key rows (``## 1 番 答え4``), so a stray
heading or a book's answer section cannot fabricate a map.

The TOC result is then cross-checked against the body: the fraction of
candidate titles that also reappear in the document's body pages is a
soft confidence measure (the TOC pages themselves are excluded — their
titles trivially appear there). Gate: ≥0.7 trust the TOC as-is; 0.3–0.7
the OCR drifted some titles, so body headings are preferred (no chapter
is dropped on title drift); <0.3 the TOC cannot be confirmed, yielding
an empty map — the optional SLM escalation hooks in here (ticket 03).
A document with no body pages has nothing to refute the scan → trusted.

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

# Content-association cross-check gate (soft confidence signal).
CONFIDENCE_HIGH = 0.7
CONFIDENCE_LOW = 0.3


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

# Workbook fallback: numbered body headings (## N <title> / ## N -A <title>)
# with no 課/章 marker. Unlike marker-based chapters, repeated numbers are
# distinct lessons (numbering resets per section), so no dedup by number.
_NUMBERED_MIN = 3
_NUMBERED_SECTION_RE = re.compile(r"^\s*#{1,3}\s+(\d{1,2})\s+(.+?)\s*$")
# Answer-key rows: the OCR glues the answer to 番, with or without a space
# ("## 1 番 答え4", "## 3 番B51", bare "## 3 番"). A numbered title starting
# with 番 is answer-key noise — except the real words 番組 (program) and
# 番号 (number), which survive the negative lookahead.
_ANSWER_KEY_RE = re.compile(r"^番(?!組|号)")
# PaddleOCR reads a kanji title's furigana as space-separated kana groups
# glued ahead of the kanji ("かんせつてき こた かたちゅうい 間接的な…"). Strip
# that prefix. Contiguous kana words (あいさつ表現, はじめに) are kept: no
# space precedes the kanji, so the pattern cannot match them.
_KANA_PREFIX_RE = re.compile(
    r"^((?:[぀-ゟ]+\s+){1,3}[぀-ゟ]+)\s+(?=[一-鿿])"
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


def _normalize(text: str) -> str:
    """A title as it reappears in the body may differ in digit width and
    spacing (１ vs 1, 半角 vs 全角 spaces) — fold those away for the
    soft cross-check."""
    return text.translate(_FULLWIDTH_DIGITS).replace(" ", "").replace("　", "")


def _cross_check_confidence(
    entries: list[Entry], toc_pages: set[int], markdown: str
) -> float:
    """Soft cross-check: the fraction of TOC candidate titles that also
    reappear in the document's body pages.

    Pages that carried the TOC entries themselves are excluded — their
    titles trivially appear there, so including them would make every
    TOC self-confirming. With no body pages at all there is nothing to
    refute the scan, so it is trusted (confidence 1.0).
    """
    body = [body for n, body in split_pages(markdown) if n not in toc_pages]
    if not body:
        return 1.0
    normalized_body = _normalize("\n".join(body))
    matched = sum(
        1 for e in entries if _normalize(e["chapter_title"]) in normalized_body
    )
    return matched / len(entries)


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


def _extract_entries(
    markdown: str, language: str | None = None
) -> tuple[list[Entry], set[int]]:
    """Scan every page for part headers and chapter entries.

    Returns ``(entries, toc_pages)`` — the second is the set of pages
    that carried at least one chapter entry, i.e. the TOC pages, which
    the cross-check must exclude from the body.
    """
    entries: list[Entry] = []
    toc_pages: set[int] = set()
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

            toc_pages.add(page_num)  # any chapter-looking line marks a TOC page
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
    return entries, toc_pages


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


def _extract_numbered_sections(
    markdown: str, language: str | None = None
) -> list[Entry]:
    """Workbook fallback: chapters from numbered body headings.

    A listening/grammar workbook numbers its lessons (``## 2 ポイント理解``,
    ``## 1 -A 間違えやすい音``) but carries no 課/章 marker, so neither the
    TOC scan nor the marker-based body scan can see them. Conservative by
    design: answer-key rows (``## 1 番 答え4``) and practice sections are
    excluded, a kana reading prefix the OCR glued ahead of the kanji title
    is stripped, and at least ``_NUMBERED_MIN`` headings must survive or no
    map is produced. Repeated numbers are distinct lessons (the numbering
    resets per section), so occurrences are never deduplicated.
    """
    entries: list[Entry] = []
    stop = _stoplist(language)
    for page_num, body in split_pages(markdown):
        for line in body.split("\n"):
            match = _NUMBERED_SECTION_RE.match(line.translate(_FULLWIDTH_DIGITS))
            if not match:
                continue
            topic = match.group(2).strip()
            if _ANSWER_KEY_RE.match(topic) or stop.search(topic):
                continue
            topic = _KANA_PREFIX_RE.sub("", topic, count=1)
            if not topic:
                continue
            entries.append({
                "part": "",
                "chapter_num": int(match.group(1)),
                "chapter_title": topic[:200],
                "page": page_num,
            })
    if len(entries) < _NUMBERED_MIN:
        return []
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

    The TOC dotted-anchor scan handles 課-based TOCs (GOI); a content
    cross-check confirms it (or prefers body headings when the OCR
    drifted the titles); when the scan finds nothing the extraction
    falls back to body headings (章-based books like the N3 Kanji book),
    then to numbered body headings (workbook-style books like the N3
    CHOUKAI listening book).
    """
    toc_entries, toc_pages = _extract_entries(markdown, language)
    toc_entries = [e for e in toc_entries if e["page"]]

    if toc_entries:
        confidence = _cross_check_confidence(toc_entries, toc_pages, markdown)
        if confidence < CONFIDENCE_LOW:
            # The TOC cannot be confirmed against the body — no map. The
            # current lesson fallback runs; the SLM escalation hooks in
            # here (ticket 03).
            return []
        if confidence < CONFIDENCE_HIGH:
            # The OCR drifted some titles: prefer the body headings (no
            # chapter is dropped on title drift); keep the TOC only if
            # the body carries no readable headings at all.
            body = _extract_body_chapters(markdown, language)
            entries = body if body else toc_entries
        else:
            entries = toc_entries
    else:
        entries = _extract_body_chapters(markdown, language)
        if not entries:
            entries = _extract_numbered_sections(markdown, language)

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
