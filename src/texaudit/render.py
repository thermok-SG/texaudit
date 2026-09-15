"""Render structured audit reports for human-readable terminal output."""

from __future__ import annotations

from .models import AuditReport


def render_terminal(report: AuditReport) -> str:
    """Render an audit report as aligned plain text without ANSI styling."""

    s = report.stats
    agu_profile = any(check.name == "Publication units" for check in report.checks)
    lines = [
        f"Manuscript audit: {s.source}",
        f"Journal profile: {report.profile_name}",
        "",
        "TEXT",
        f"  Title:                    {s.title_words} words",
        f"  Abstract:                 {s.abstract_words} words",
        f"  Plain language summary:   {s.plain_language_summary_words} words",
        f"  Body text:                {s.body_words} words",
        f"  Methods (within body):    {s.methods_words} words",
        f"  Acknowledgements:         {s.acknowledgements_words} words",
        f"  Appendices:               {s.appendix_words} words",
        f"  Figure captions:          {s.figure_caption_words} words",
        f"  Table captions:           {s.table_caption_words} words",
        f"  Table cell text:          {s.table_text_words} words" + (" (excluded from AGU total)" if agu_profile else ""),
        f"  Open Research:            {s.open_research_words} words" + (" (excluded from AGU total)" if agu_profile else ""),
        f"  Equations:                {s.equation_count}" + (" (one word each in AGU total)" if agu_profile else ""),
    ]
    if agu_profile:
        lines.append(f"  AGU counted words:        {s.agu_word_count}")
    lines.extend([
        "",
        "DISPLAY ITEMS",
        f"  Figures:                  {s.figure_count}",
        f"  Tables:                   {s.table_count}",
        f"  Subfigures/subtables:     {s.subfigure_count}",
        f"  Citation commands:        {s.citation_command_count}",
        f"  References:               {s.reference_count}",
        "",
        "CHECKS",
    ])
    for check in report.checks:
        lines.append(f"  {check.status:<7} {check.name}: {check.message}")
    lines.extend([
        "",
        f"OVERALL: {report.overall_status}",
        f"Files read: {len(s.files_read)}",
    ])
    return "\n".join(lines)
