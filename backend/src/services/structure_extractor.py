"""Structure Extractor — parses OCR markdown to extract document structure.

Handles: Table of Contents parsing, chapter/section detection,
topic grouping, and table structure recovery from raw OCR text.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """A chapter/section extracted from the document."""
    number: int
    title_jp: str
    title_en: str = ""
    page_start: int = 0
    topic: str = ""
    part: str = ""  # "Part 1" or "Part 2"
    estimated_pages: int = 0  # pages in this chapter


@dataclass
class DocumentStructure:
    """Full document structure extracted from OCR output."""
    title: str = ""
    authors: list[str] = field(default_factory=list)
    language: str = "ja"
    total_chapters: int = 0
    total_vocabulary: int = 0  # extracted from preface
    parts: list[str] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    raw_toc_text: str = ""


# Pattern: "N課 <everything> <page_number>" — captures chapter number, full title, and page
CHAPTER_LINE = re.compile(
    r'(?P<num>\d{1,2})\s*課\s+'
    r'(?P<full_title>.+?)'
    r'(?:[.…]+\s*)?'       # Optional dot leaders
    r'(?P<page>\d{1,3})'   # Page number (1-3 digits)
    r'(?:\s|$)',           # Must end with whitespace or EOL
    re.MULTILINE,
)

# Pattern: Part headers
PART_HEADER = re.compile(
    r'第(?P<part_num>\d)部\s+(?P<part_title>.+?)\s+'
    r'Part\s+\d+',
    re.MULTILINE,
)

# All chapter patterns to try (in order)
TOC_PATTERNS = [CHAPTER_LINE]


def _split_title(full_title: str) -> tuple[str, str]:
    """Split a combined title into Japanese and English parts.

    Heuristic: the split point is where the first ASCII letter sequence begins
    after a run of CJK/numeric/punctuation characters.
    """
    # Find the boundary: last CJK/punctuation char followed by space + ASCII uppercase
    m = re.search(r'[一-龯ぁ-んァ-ヶ：、。・（）\d]\s{2,}(?=[A-Z])', full_title)
    if m:
        split_pos = m.end() - 1  # Position of the space(s) before English
        # Walk back to find the actual boundary
        jp = full_title[:m.start() + 1].strip()
        en = full_title[m.end():].strip() if m.end() < len(full_title) else ""
        return jp, en

    # Fallback: if the title has mixed content, try to split at first English word
    m2 = re.search(r'\s{2,}(?=[A-Z][a-z])', full_title)
    if m2:
        jp = full_title[:m2.start()].strip()
        en = full_title[m2.end():].strip()
        return jp, en

    return full_title.strip(), ""

# Topic keywords for grouping chapters
TOPIC_KEYWORDS = {
    "human_relations": ["人間関係", "家族", "友達", "性格", "付き合い", "気持ち"],
    "daily_life": ["生活", "毎日", "食生活", "家"],
    "body_health": ["体", "美容", "健康", "病気"],
    "hobbies_travel": ["趣味", "旅行", "スポーツ", "芸術", "ファッション"],
    "education": ["教育", "学校", "大学", "小中高"],
    "work": ["仕事", "コンピューター", "郵便", "電話"],
    "society": ["社会", "事件", "事故", "政治", "経済", "行事", "宗教"],
    "nature": ["自然", "季節", "天気", "地理", "植物", "動物"],
    "numbers_time": ["数", "量", "時間"],
    "grammar_word_types": ["動詞", "形容詞", "副詞", "オノマトペ", "漢語", "和語", "語形成", "言い換え"],
}


def classify_topic(title_jp: str) -> str:
    """Map a chapter title to a topic category based on keywords."""
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in title_jp:
                return topic
    return "general"


def extract_toc(markdown_text: str) -> DocumentStructure:
    """Extract table of contents structure from HPD markdown output.

    Works with raw OCR text that contains page markers like:
    '--- Page 5 ---' followed by TOC entries.
    """
    structure = DocumentStructure()
    seen_keys = set()  # Track (part, number) pairs instead of just numbers

    # Find TOC pages — pages containing "目次" or numbered chapter entries
    toc_pages = []
    for page_match in re.finditer(r'--- Page (\d+) ---\n(.*?)(?=--- Page \d+ ---|$)', markdown_text, re.DOTALL):
        page_num = int(page_match.group(1))
        page_content = page_match.group(2)
        if '目次' in page_content or 'Contents' in page_content:
            toc_pages.append((page_num, page_content))

    if not toc_pages:
        # Fallback: look for pages with numbered chapter patterns
        for page_match in re.finditer(r'--- Page (\d+) ---\n(.*?)(?=--- Page \d+ ---|$)', markdown_text, re.DOTALL):
            page_num = int(page_match.group(1))
            page_content = page_match.group(2)
            chapters_found = len(re.findall(r'\d{1,2}\s*課\s+', page_content))
            if chapters_found >= 3:
                toc_pages.append((page_num, page_content))

    # Merge all TOC page content
    all_toc_text = '\n'.join(content for _, content in toc_pages)
    structure.raw_toc_text = all_toc_text

    # Detect parts and their boundaries in TOC text
    part_boundaries = []
    for m in PART_HEADER.finditer(all_toc_text):
        part_label = f"Part {m.group('part_num')}: {m.group('part_title').strip()}"
        if part_label not in structure.parts:
            structure.parts.append(part_label)
            part_boundaries.append((m.start(), m.group('part_num')))

    # Extract chapters using multiple patterns
    current_part = "Part 1" if structure.parts else ""
    for pattern in TOC_PATTERNS[:2]:  # Use only chapter patterns
        for m in pattern.finditer(all_toc_text):
            num = int(m.group('num'))

            # Determine which part this chapter belongs to
            for boundary_pos, part_num in part_boundaries:
                if m.start() > boundary_pos:
                    current_part = f"Part {part_num}"

            key = (current_part, num)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            title_jp = m.group('full_title').strip().rstrip('….').strip()
            title_en = ""
            page = int(m.group('page'))
            topic = classify_topic(title_jp)

            # Try to split Japanese/English parts
            title_jp, title_en = _split_title(title_jp)

            chapter = Chapter(
                number=num,
                title_jp=title_jp,
                title_en=title_en,
                page_start=page,
                topic=topic,
                part=current_part,
            )
            structure.chapters.append(chapter)

    # Sort by chapter number
    structure.chapters.sort(key=lambda c: c.number)
    structure.total_chapters = len(structure.chapters)

    # Estimate pages per chapter
    for i, ch in enumerate(structure.chapters):
        if i < len(structure.chapters) - 1:
            ch.estimated_pages = structure.chapters[i + 1].page_start - ch.page_start
        else:
            ch.estimated_pages = 10  # Default for last chapter

    # Extract metadata from preface
    _extract_metadata(markdown_text, structure)

    logger.info(
        f"Extracted structure: {structure.total_chapters} chapters, "
        f"{len(structure.parts)} parts, {structure.total_vocabulary} vocab items"
    )
    return structure


def _extract_metadata(markdown_text: str, structure: DocumentStructure) -> None:
    """Extract book metadata from preface/content pages."""
    # Try to find total vocabulary count
    vocab_match = re.search(r'語彙[^\d]*?(\d{1,3}(?:,\d{3})*)\s*語', markdown_text)
    if vocab_match:
        structure.total_vocabulary = int(vocab_match.group(1).replace(',', ''))

    # Try to find title
    title_match = re.search(r'(新完全マスタ[ー－]\s*[^\n]{2,20})', markdown_text)
    if title_match:
        structure.title = title_match.group(1).strip()

    # Try to find author
    author_match = re.search(r'(?:著|著者)[：:\s]*([^\n]{5,40})', markdown_text)
    if author_match:
        structure.authors = [a.strip() for a in author_match.group(1).split('・')]


def extract_chapter_content(markdown_text: str, chapter: Chapter) -> str:
    """Extract the content for a specific chapter from the full markdown.

    Uses page start/end hints and chapter title to locate content.
    """
    pages = re.split(r'--- Page \d+ ---', markdown_text)
    results = []

    for i, page_content in enumerate(pages):
        page_num = i + 1
        if chapter.page_start > 0 and page_num < chapter.page_start:
            continue
        if chapter.estimated_pages > 0 and page_num >= chapter.page_start + chapter.estimated_pages + 2:
            break

        # Check if this page contains the chapter title or related content
        if (chapter.title_jp[:5] in page_content or
                str(chapter.number) + '課' in page_content or
                chapter.page_start <= page_num <= chapter.page_start + chapter.estimated_pages):
            results.append(page_content)

    return '\n'.join(results)


def extract_vocabulary_from_content(content: str) -> list[dict]:
    """Extract vocabulary items from chapter content.

    Looks for Japanese word patterns: kanji + reading in parentheses.
    """
    vocab_items = []
    # Pattern: 漢字(かんじ) or 言葉【ことば】
    patterns = [
        re.compile(r'([一-龯ぁ-んァ-ヶ]{2,8})[（(]([ぁ-んァ-ヶ]{1,10})[）)]'),
        re.compile(r'([一-龯ぁ-んァ-ヶ]{2,8})【([ぁ-んァ-ヶ]{1,10})】'),
    ]

    for pattern in patterns:
        for m in pattern.finditer(content):
            word = m.group(1)
            reading = m.group(2)
            vocab_items.append({
                "word": word,
                "reading": reading,
                "source_chapter": 0,
            })

    return vocab_items


def generate_table_of_contents(structure: DocumentStructure) -> str:
    """Generate a clean markdown table of contents from extracted structure."""
    lines = [f"# {structure.title or 'Document'} — Table of Contents\n"]

    for part in structure.parts:
        lines.append(f"## {part}\n")

    current_part = ""
    for ch in structure.chapters:
        if ch.part and ch.part != current_part:
            current_part = ch.part
            if current_part not in '\n'.join(lines):
                lines.append(f"## {current_part}\n")

        en_suffix = f" — {ch.title_en}" if ch.title_en else ""
        page_info = f" (p.{ch.page_start})" if ch.page_start else ""
        lines.append(f"{ch.number}. **{ch.title_jp}**{en_suffix}{page_info}  ")
        lines.append(f"   Topic: `{ch.topic}` | ~{ch.estimated_pages} pages\n")

    if structure.total_vocabulary:
        lines.append(f"\n---\n*Total vocabulary: ~{structure.total_vocabulary:,} words*")

    return '\n'.join(lines)
