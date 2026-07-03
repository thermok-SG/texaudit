from __future__ import annotations

import re
from pathlib import Path

from docx import Document

from .counting import count_characters, count_words
from .models import ManuscriptStats
from .parser import ACK_NAMES, APPENDIX_NAMES, OPEN_RESEARCH_NAMES, normalise_name

ABSTRACT_NAMES = {"abstract"}
PLS_NAMES = {"plain language summary", "plain-language summary", "plainlanguagesummary", "pls"}
KEYPOINT_NAMES = {"key points", "keypoints", "key_points"}
REFERENCE_NAMES = {"references", "bibliography", "reference list"}
CAPTION_RE = re.compile(r"^\s*(figure|fig\.?|table)\s*(?:s\.?\s*)?(\d+[a-zA-Z]?)?\s*[:.\-]", re.I)


def _paragraph_is_heading(paragraph) -> bool:
    style_name = (getattr(paragraph.style, "name", "") or "").lower()
    return style_name.startswith("heading") or style_name in {"title", "subtitle"}


def _caption_kind(paragraph) -> str | None:
    text = paragraph.text.strip()
    style_name = (getattr(paragraph.style, "name", "") or "").lower()
    match = CAPTION_RE.match(text)
    if "caption" in style_name or match:
        if match and match.group(1).lower().startswith("t"):
            return "table"
        if match and match.group(1).lower().startswith("f"):
            return "figure"
        # Word's Caption style does not identify item type; infer from text where possible.
        if text.lower().startswith("table"):
            return "table"
        return "figure"
    return None


def _drawing_count(document) -> int:
    # Inline shapes miss floating images; counting w:drawing catches both.
    try:
        return len(document.element.body.xpath(".//w:drawing"))
    except Exception:
        return len(document.inline_shapes)


def _equation_count(document) -> int:
    try:
        displayed = document.element.body.xpath(".//m:oMathPara")
        if displayed:
            return len(displayed)
        return len(document.element.body.xpath(".//m:oMath"))
    except Exception:
        return 0


def _citation_count(document) -> int:
    try:
        instructions = document.element.body.xpath(".//w:instrText")
        return sum(1 for item in instructions if "CITATION" in (item.text or "").upper() or " CITE " in f" {(item.text or '').upper()} ")
    except Exception:
        return 0


def parse_docx(path: Path) -> ManuscriptStats:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"DOCX file not found: {path}")
    document = Document(path)
    stats = ManuscriptStats(source=str(path), files_read=[str(path)])
    stats.figure_count = _drawing_count(document)
    stats.table_count = len(document.tables)
    stats.equation_count = _equation_count(document)
    stats.citation_command_count = _citation_count(document)

    current = "body"
    key_items: list[str] = []
    seen_heading_names: list[str] = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        name = normalise_name(text.rstrip(":"))
        is_named_heading = name in (ABSTRACT_NAMES | PLS_NAMES | KEYPOINT_NAMES | REFERENCE_NAMES | ACK_NAMES | APPENDIX_NAMES | OPEN_RESEARCH_NAMES)
        if _paragraph_is_heading(paragraph) or is_named_heading:
            if is_named_heading:
                current = name
                seen_heading_names.append(name)
                continue
            # Styled headings are retained as body structure but do not count as prose.
            seen_heading_names.append(name)
            current = "appendix" if name.startswith("appendix") else "body"
            continue

        caption_kind = _caption_kind(paragraph)
        if caption_kind == "figure":
            stats.figure_caption_words += count_words(text)
            continue
        if caption_kind == "table":
            stats.table_caption_words += count_words(text)
            continue

        if current in ABSTRACT_NAMES:
            stats.abstract_words += count_words(text)
        elif current in PLS_NAMES:
            stats.plain_language_summary_words += count_words(text)
        elif current in KEYPOINT_NAMES:
            key_items.append(text)
        elif current in REFERENCE_NAMES:
            stats.reference_words += count_words(text)
        elif current in ACK_NAMES:
            stats.acknowledgements_words += count_words(text)
        elif current in APPENDIX_NAMES or current.startswith("appendix"):
            stats.appendix_words += count_words(text)
        elif current in OPEN_RESEARCH_NAMES:
            stats.open_research_words += count_words(text)
        else:
            stats.body_words += count_words(text)

    stats.section_names = seen_heading_names
    stats.key_point_count = len(key_items)
    stats.key_point_max_characters = max((count_characters(item) for item in key_items), default=0)

    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                stats.table_text_words += count_words(cell.text)

    # Normal Word text cannot expose TeX-style unresolved refs, but literal markers are still useful.
    all_text = "\n".join(p.text for p in document.paragraphs)
    stats.unresolved_marker_count = all_text.count("??")
    if stats.figure_count == 0:
        stats.warnings.append("No embedded Word drawings detected. Linked images or externally supplied figures are not counted.")
    stats.warnings.append("DOCX citation detection only recognises Word field-code citations; Zotero, EndNote, and plain-text citations may not be counted.")
    return stats
