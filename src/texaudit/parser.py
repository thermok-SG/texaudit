from __future__ import annotations

import re
from pathlib import Path

from .counting import MATH_ENVS, count_characters, count_words
from .models import ManuscriptStats
from .tex import BEGIN_END_RE, SECTION_RE, command_argument_blocks, command_arguments, extract_environment_blocks, load_tex, remove_spans

FIGURE_ENVS = {"figure", "figure*"}
TABLE_ENVS = {"table", "table*", "longtable"}
REFERENCE_ENVS = {"thebibliography", "references"}
ACK_NAMES = {"acknowledgements", "acknowledgments"}
APPENDIX_NAMES = {"appendix", "appendices"}
OPEN_RESEARCH_NAMES = {"open research statement", "open research", "data availability", "data and code availability"}
PLS_NAMES = {"plain language summary", "plain-language summary", "plainlanguagesummary", "pls"}
HIGHLIGHT_NAMES = {"highlights", "research highlights"}
TOP_SECTION_RE = re.compile(r"\\section\*?\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}")


def normalise_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _first_environment_content(text: str, names: list[str]) -> tuple[str, list[tuple[int, int]]]:
    for name in names:
        blocks = extract_environment_blocks(text, name)
        if blocks:
            return blocks[0][2], [(item[0], item[1]) for item in blocks]
    return "", []


def _extract_sections(text: str) -> list[tuple[int, int, str, str]]:
    matches = list(SECTION_RE.finditer(text))
    sections: list[tuple[int, int, str, str]] = []
    for idx, match in enumerate(matches):
        start = match.start()
        content_start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        sections.append((start, end, normalise_name(match.group(1)), text[content_start:end]))
    return sections


def _caption_text(block: str) -> str:
    captions = command_arguments(block, "caption") + command_arguments(block, "captionof")
    return " ".join(captions)


def _count_bib_entries(text: str) -> int:
    if "\\bibitem" in text:
        return len(re.findall(r"\\bibitem(?:\[[^\]]*\])?\{", text))
    return 0


def parse_manuscript(path: Path, *, follow_inputs: bool = True) -> ManuscriptStats:
    text, files, warnings = load_tex(path, follow_inputs=follow_inputs)
    stats = ManuscriptStats(source=str(path), files_read=files, warnings=warnings)
    stats.environment_names = sorted({m.group(2) for m in BEGIN_END_RE.finditer(text)})
    stats.section_names = [normalise_name(m.group(1)) for m in SECTION_RE.finditer(text)]
    stats.unresolved_marker_count = text.count("??")
    stats.citation_command_count = len(re.findall(r"\\(?:cite|citep|citet|parencite|textcite|autocite|footcite)\*?(?:\[[^\]]*\]){0,2}\s*\{", text))

    title = command_arguments(text, "title")
    stats.title_words = count_words(title[0]) if title else 0
    stats.title_characters = count_characters(title[0]) if title else 0

    pls, pls_spans = _first_environment_content(text, ["plainlanguagesummary", "plain_language_summary", "pls"])
    stats.plain_language_summary_words = count_words(pls)

    abstract, abstract_spans = _first_environment_content(text, ["abstract"])
    # The official agujournal2025 template nests the PLS inside the abstract.
    # It is visually distinct and excluded from AGU's publication-unit count.
    nested_pls_spans: list[tuple[int, int]] = []
    for name in ["plainlanguagesummary", "plain_language_summary", "pls"]:
        nested_pls_spans.extend((start, end) for start, end, _ in extract_environment_blocks(abstract, name))
    stats.abstract_words = count_words(remove_spans(abstract, nested_pls_spans))

    keypoints, keypoints_spans = _first_environment_content(text, ["keypoints", "key_points"])
    items = re.split(r"\\item(?:\s|\{|$)", keypoints)
    key_items = [item for item in items[1:] if count_words(item) > 0]
    # agujournal2025 replaced the environment with a three-argument command;
    # empty braces are placeholders and do not constitute key points.
    keypoint_command_spans: list[tuple[int, int]] = []
    for start, end, arguments in command_argument_blocks(text, "keypoints", 3):
        key_items.extend(item for item in arguments if count_words(item) > 0)
        keypoint_command_spans.append((start, end))
    stats.key_point_count = len(key_items)
    stats.key_point_max_characters = max((count_characters(item) for item in key_items), default=0)

    highlights, highlight_spans = _first_environment_content(text, ["highlights", "researchhighlights"])
    highlight_items = [item for item in re.split(r"\\item(?:\s|\{|$)", highlights)[1:] if count_words(item) > 0]
    stats.highlight_count = len(highlight_items)
    stats.highlight_max_characters = max((count_characters(item) for item in highlight_items), default=0)

    figure_spans: list[tuple[int, int]] = []
    table_spans: list[tuple[int, int]] = []
    for env in FIGURE_ENVS:
        blocks = extract_environment_blocks(text, env)
        stats.figure_count += len(blocks)
        figure_spans.extend((start, end) for start, end, _ in blocks)
        stats.figure_caption_words += sum(count_words(_caption_text(block)) for _, _, block in blocks)
        stats.subfigure_count += sum(len(extract_environment_blocks(block, "subfigure")) + len(extract_environment_blocks(block, "subtable")) for _, _, block in blocks)
    for env in TABLE_ENVS:
        blocks = extract_environment_blocks(text, env)
        stats.table_count += len(blocks)
        table_spans.extend((start, end) for start, end, _ in blocks)
        stats.table_caption_words += sum(count_words(_caption_text(block)) for _, _, block in blocks)
        # In an MVP, all table content other than captions is reported but excluded from AGU total.
        for _, _, block in blocks:
            stripped = block
            for cap in command_arguments(block, "caption"):
                stripped = stripped.replace(cap, "")
            stats.table_text_words += count_words(stripped)

    equation_spans: list[tuple[int, int]] = []
    for env in MATH_ENVS:
        blocks = extract_environment_blocks(text, env)
        stats.equation_count += len(blocks)
        equation_spans.extend((start, end) for start, end, _ in blocks)
    stats.equation_count += len(re.findall(r"(?s)\\\[.*?\\\]", text))
    stats.equation_count += len(re.findall(r"(?s)(?<!\\)\$\$.*?\$\$", text))

    sections = _extract_sections(text)
    section_spans: list[tuple[int, int]] = []
    # Remove nested display and bibliography material before counting named prose sections.
    def prose_only(content: str) -> str:
        spans: list[tuple[int, int]] = []
        for env in FIGURE_ENVS | TABLE_ENVS | MATH_ENVS | REFERENCE_ENVS:
            spans.extend((start, end) for start, end, _ in extract_environment_blocks(content, env))
        return remove_spans(content, spans)

    top_sections = list(TOP_SECTION_RE.finditer(text))
    for index, match in enumerate(top_sections):
        name = re.sub(r"^\d+(?:\.\d+)*\s+", "", normalise_name(match.group(1)))
        if name in {"methods", "online methods", "materials and methods"}:
            end = top_sections[index + 1].start() if index + 1 < len(top_sections) else len(text)
            stats.methods_words += count_words(prose_only(text[match.start():end]))

    for start, end, name, content in sections:
        content = prose_only(content)
        if name in PLS_NAMES and stats.plain_language_summary_words == 0:
            # Support the agujournal2019-style unnumbered PLS section too.
            stats.plain_language_summary_words += count_words(content)
            section_spans.append((start, end))
        elif name in ACK_NAMES:
            stats.acknowledgements_words += count_words(content)
            section_spans.append((start, end))
        elif name in APPENDIX_NAMES or name.startswith("appendix"):
            stats.appendix_words += count_words(content)
            section_spans.append((start, end))
        elif name in OPEN_RESEARCH_NAMES:
            stats.open_research_words += count_words(content)
            section_spans.append((start, end))

    reference_spans: list[tuple[int, int]] = []
    for env in REFERENCE_ENVS:
        blocks = extract_environment_blocks(text, env)
        reference_spans.extend((start, end) for start, end, _ in blocks)
        stats.reference_words += sum(count_words(block) for _, _, block in blocks)
        stats.reference_count += sum(_count_bib_entries(block) for _, _, block in blocks)
    # A BibTeX declaration means entries live outside source; we only surface this as a warning.
    if re.search(r"\\(?:bibliography|addbibresource)\s*\{", text) and not reference_spans:
        stats.warnings.append("Bibliography declaration found, but reference entries are external and were not counted. Supply a .bbl input if you need entry-level reference auditing.")

    protected_spans = abstract_spans + pls_spans + keypoints_spans + keypoint_command_spans + highlight_spans + figure_spans + table_spans + equation_spans + section_spans + reference_spans
    remaining = remove_spans(text, protected_spans)
    # Remove preamble/title/front-matter before document begins.
    begin_doc = re.search(r"\\begin\s*\{document\}", remaining)
    if begin_doc:
        remaining = remaining[begin_doc.end():]
    end_doc = re.search(r"\\end\s*\{document\}", remaining)
    if end_doc:
        remaining = remaining[:end_doc.start()]
    # remove title and common AGU front matter calls
    remaining = re.sub(r"\\(?:title|authors|author|affiliation|correspondingauthor|journalname|keywords)\s*(?:\[[^\]]*\])?\s*\{(?:[^{}]|\{[^{}]*\})*\}", " ", remaining, flags=re.S)
    stats.body_words = count_words(remaining)
    return stats
