"""Best-effort reader for plain-text and Markdown manuscripts.

Section boundaries are inferred from standalone heading-like lines. Unlike the
TeX and DOCX readers, this reader has no reliable structural metadata and always
adds a warning explaining that its measurements are estimates.
"""

from __future__ import annotations

import re
from pathlib import Path

from .counting import count_characters, count_words
from .models import ManuscriptStats
from .parser import ACK_NAMES, APPENDIX_NAMES, OPEN_RESEARCH_NAMES, matches_section_name, normalise_name

ABSTRACT_NAMES = {"abstract"}
PLS_NAMES = {"plain language summary", "plain-language summary", "plainlanguagesummary", "pls"}
KEYPOINT_NAMES = {"key points", "keypoints", "key_points"}
HIGHLIGHT_NAMES = {"highlights", "research highlights"}
REFERENCE_NAMES = {"references", "bibliography", "reference list"}
CAPTION_RE = re.compile(r"^\s*(figure|fig\.?|table)\s*(?:s\.?\s*)?\d+[a-zA-Z]?\s*[:.\-]", re.I)


def parse_text(path: Path) -> ManuscriptStats:
    """Extract manuscript measurements from a UTF-8 text or Markdown file.

    Args:
        path: Source file to read. Invalid UTF-8 bytes are replaced.

    Returns:
        Best-effort, format-independent manuscript statistics.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """

    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    raw = path.read_text(encoding="utf-8", errors="replace")
    stats = ManuscriptStats(source=str(path), files_read=[str(path)])
    current = "body"
    key_items: list[str] = []
    highlights: list[str] = []

    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        name = normalise_name(text.rstrip(":"))
        exact_heading_names = ABSTRACT_NAMES | PLS_NAMES | KEYPOINT_NAMES | HIGHLIGHT_NAMES | REFERENCE_NAMES | ACK_NAMES | APPENDIX_NAMES
        is_open_research_heading = matches_section_name(name, OPEN_RESEARCH_NAMES)
        if name in exact_heading_names or is_open_research_heading:
            current = "open research" if is_open_research_heading else name
            stats.section_names.append(name)
            continue
        if CAPTION_RE.match(text):
            if text.lower().startswith("table"):
                stats.table_caption_words += count_words(text)
                stats.table_count += 1
            else:
                stats.figure_caption_words += count_words(text)
                stats.figure_count += 1
            continue
        if current in ABSTRACT_NAMES:
            stats.abstract_words += count_words(text)
        elif current in PLS_NAMES:
            stats.plain_language_summary_words += count_words(text)
        elif current in KEYPOINT_NAMES:
            if text.startswith(('-', '•', '*')):
                key_items.append(text.lstrip('-•* ').strip())
            else:
                key_items.append(text)
        elif current in HIGHLIGHT_NAMES:
            highlights.append(text.lstrip('-•* ').strip())
        elif current in REFERENCE_NAMES:
            stats.reference_words += count_words(text)
            stats.reference_count += 1
        elif current in ACK_NAMES:
            stats.acknowledgements_words += count_words(text)
        elif current in APPENDIX_NAMES or current.startswith("appendix"):
            stats.appendix_words += count_words(text)
        elif current in OPEN_RESEARCH_NAMES:
            stats.open_research_words += count_words(text)
        else:
            stats.body_words += count_words(text)

    stats.key_point_count = len(key_items)
    stats.key_point_max_characters = max((count_characters(item) for item in key_items), default=0)
    stats.highlight_count = len(highlights)
    stats.highlight_max_characters = max((count_characters(item) for item in highlights), default=0)
    stats.unresolved_marker_count = raw.count("??")
    stats.warnings.append("Plain-text mode is an estimate: it cannot reliably distinguish embedded figures, tables, equations, captions, tracked changes, or Word styles.")
    return stats
