from pathlib import Path

from texaudit.audit import audit
from texaudit.parser import parse_manuscript
from texaudit.profiles import load_profile


def test_public_class_runs_an_audit():
    from texaudit import TexAudit

    fixture = Path(__file__).parent / "fixtures" / "sample.tex"
    report = TexAudit(journal="agu-jgr-earth-surface").audit(fixture)
    assert report.profile_name == "AGU — JGR: Earth Surface"
    assert report.stats.abstract_words > 0


def test_parse_sample():
    fixture = Path(__file__).parent / "fixtures" / "sample.tex"
    stats = parse_manuscript(fixture)
    assert stats.abstract_words > 0
    assert stats.plain_language_summary_words > 0
    assert stats.figure_count == 1
    assert stats.table_count == 1
    assert stats.equation_count == 1
    assert stats.key_point_count == 2
    assert stats.body_words > 0
    assert any("child.tex" in item for item in stats.files_read)


def test_parse_official_agu_2025_structure():
    fixture = Path(__file__).parent / "fixtures" / "agu2025.tex"
    stats = parse_manuscript(fixture)
    assert stats.abstract_words == 6
    assert stats.plain_language_summary_words == 7
    assert stats.key_point_count == 2
    assert stats.key_point_max_characters == len("Second formatted key point")
    assert stats.body_words == 8
    assert stats.agu_word_count == 14


def test_sideways_figures_combined_availability_heading_and_matching_bbl(tmp_path):
    manuscript = tmp_path / "article.tex"
    manuscript.write_text(
        r"""
        \begin{document}
        \begin{figure}\caption{First}\end{figure}
        \begin{sidewaysfigure}\caption{Second}\end{sidewaysfigure}
        \section*{Software environment and Data availability}
        Data and software are archived in repositories.
        \bibliography{references}
        \end{document}
        """,
        encoding="utf-8",
    )
    manuscript.with_suffix(".bbl").write_text(
        r"""
        \begin{thebibliography}{}
        \bibitem [Optional author label]{first} First reference.
        \bibitem{second} Second reference.
        \end{thebibliography}
        """,
        encoding="utf-8",
    )

    stats = parse_manuscript(manuscript)

    assert stats.figure_count == 2
    assert stats.open_research_words == 7
    assert stats.reference_count == 2
    assert str(manuscript.with_suffix(".bbl")) in stats.files_read


def test_agu_profile_audits_sample():
    fixture = Path(__file__).parent / "fixtures" / "sample.tex"
    profile, path = load_profile("agu-jgr-earth-surface")
    report = audit(parse_manuscript(fixture), profile, path)
    names = {check.name for check in report.checks}
    assert "Publication units" in names
    assert "Abstract" in names


def test_common_agu_profiles_are_available():
    from texaudit.profiles import builtin_profile_names

    names = builtin_profile_names()
    assert "agu-grl" in names
    assert "agu-jgr-earth-surface" in names
    assert "agu-jgr-solid-earth" in names
    assert "agu-tectonics" in names
    assert "agu-water-resources-research" in names
    assert "_agu-research-article" not in names


def test_requested_earth_science_profiles_are_available():
    from texaudit.profiles import builtin_profile_names

    names = set(builtin_profile_names())
    assert {
        "aaas-science-advances-research-article",
        "cambridge-quaternary-research-research-article",
        "egu-earth-surface-dynamics-research-article",
        "egu-geoscientific-model-development-research-article",
        "egu-nhess-research-article",
        "egu-solid-earth-research-article",
        "elsevier-journal-of-structural-geology-research-article",
        "gsa-bulletin-research-article",
        "gsa-geology-article",
        "wiley-basin-research-research-article",
    } <= names


def test_generic_profile_reports_metrics_without_journal_checks():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("generic")
    stats = ManuscriptStats(source="notes.txt", body_words=1234, figure_count=2, table_count=1)
    report = audit(stats, profile, path)
    checks = {check.name: check for check in report.checks}

    assert report.profile_name == "Generic manuscript breakdown (no journal rules)"
    assert report.overall_status == "WARNING"
    assert checks["Profile coverage"].status == "WARNING"
    assert "Abstract" not in checks
    assert checks["Figures"].status == "INFO"
    assert checks["Tables"].status == "INFO"


def test_every_builtin_profile_warns_about_partial_coverage():
    from texaudit.profiles import builtin_profile_names

    for name in builtin_profile_names():
        profile, path = load_profile(name)
        report = audit(parse_manuscript(Path(__file__).parent / "fixtures" / "sample.tex"), profile, path)
        coverage = [check for check in report.checks if check.name == "Profile coverage"]
        assert len(coverage) == 1, name
        assert coverage[0].status == "WARNING", name


def test_grl_profile_overrides_shared_agu_rules():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("agu-grl")
    assert profile["sections"]["abstract"]["max_words"] == 149
    assert profile["sections"]["plain_language_summary"]["required"] is True
    stats = ManuscriptStats(source="example.tex", abstract_words=100, body_words=6001)
    report = audit(stats, profile, path)
    publication_units = next(check for check in report.checks if check.name == "Publication units")
    assert publication_units.status == "FAIL"
    assert publication_units.expected == 12


def test_required_key_points_have_a_minimum():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("agu-jgr-earth-surface")
    report = audit(ManuscriptStats(source="example.tex", abstract_words=10), profile, path)
    key_points = next(check for check in report.checks if check.name == "Key points")
    assert key_points.status == "FAIL"
    assert key_points.expected == "1-3"


def test_fully_open_access_agu_profile_reports_pus_without_fee_warning():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("agu-water-resources-research")
    report = audit(ManuscriptStats(source="example.tex", body_words=13000), profile, path)
    publication_units = next(check for check in report.checks if check.name == "Publication units")
    assert publication_units.actual == 26
    assert publication_units.status == "INFO"
    assert publication_units.expected is None


def test_parse_docx(tmp_path):
    from docx import Document

    path = tmp_path / "sample.docx"
    doc = Document()
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph("This is a compact abstract with enough words to count.")
    doc.add_heading("Plain Language Summary", level=1)
    doc.add_paragraph("This explains the study in accessible language.")
    doc.add_heading("Key Points", level=1)
    doc.add_paragraph("First point", style="List Bullet")
    doc.add_paragraph("Second point", style="List Bullet")
    doc.add_heading("Introduction", level=1)
    doc.add_paragraph("This is the manuscript body text.")
    doc.add_paragraph("Figure 1. A useful figure caption.", style="Caption")
    doc.add_paragraph("Table 1. A useful table caption.", style="Caption")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Header one"
    table.cell(0, 1).text = "Header two"
    doc.add_heading("References", level=1)
    doc.add_paragraph("Smith, A. Example reference.")
    doc.save(path)

    from texaudit.docx_reader import parse_docx
    stats = parse_docx(path)
    assert stats.abstract_words > 0
    assert stats.plain_language_summary_words > 0
    assert stats.key_point_count == 2
    assert stats.figure_caption_words > 0
    assert stats.table_caption_words > 0
    assert stats.table_count == 1
    assert stats.reference_words > 0


def test_parse_agu_word_template_styles(tmp_path):
    from docx import Document
    from docx.enum.style import WD_STYLE_TYPE
    from texaudit.docx_reader import parse_docx

    path = tmp_path / "agu-template.docx"
    doc = Document()
    for name in ("Heading-Main", "Heading-Secondary", "Affiliation", "Note", "Key Points", "Abstract", "Figure or Table Caption"):
        doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    doc.add_paragraph("A concise manuscript title", style="Title")
    doc.add_paragraph("Author Name", style="Affiliation")
    doc.add_paragraph("Corresponding author details", style="Note")
    doc.add_paragraph("Key Points", style="Heading-Main")
    doc.add_paragraph("First point", style="Key Points")
    doc.add_paragraph("Abstract", style="Heading-Main")
    doc.add_paragraph("Short abstract text", style="Abstract")
    doc.add_paragraph("Plain Language Summary", style="Abstract")
    doc.add_paragraph("Short plain summary", style="Abstract")
    doc.add_paragraph("1 Introduction", style="Heading-Main")
    doc.add_paragraph("Four words of body text")
    doc.add_paragraph("2 Materials and Methods", style="Heading-Main")
    doc.add_paragraph("2.1 Tests", style="Heading-Secondary")
    doc.add_paragraph("Three method words")
    doc.add_paragraph("3 Results", style="Heading-Main")
    doc.add_paragraph("Two result words")
    caption = "Figure 1. One numbered caption"
    doc.add_paragraph(caption)
    doc.add_paragraph(caption, style="Figure or Table Caption")
    doc.add_paragraph("Table 1. One table caption", style="Figure or Table Caption")
    doc.add_paragraph("References")
    doc.add_paragraph("First reference")
    doc.add_paragraph("Second reference")
    doc.save(path)

    stats = parse_docx(path)
    assert stats.title_words == 4
    assert stats.body_words == 11
    assert stats.methods_words == 3
    assert stats.figure_count == 1
    assert stats.table_count == 1
    assert stats.figure_caption_words == 5
    assert stats.reference_count == 2


def test_nature_geoscience_limits_and_guidance():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("nature-geoscience-article")
    stats = ManuscriptStats(
        source="example.docx",
        title_characters=91,
        abstract_words=150,
        body_words=4000,
        methods_words=1500,
        figure_count=5,
        table_count=2,
        reference_count=51,
        section_names=["data availability"],
    )
    report = audit(stats, profile, path)
    checks = {check.name: check for check in report.checks}
    assert checks["Title"].status == "FAIL"
    assert checks["Main text"].actual == 2500
    assert checks["Main text"].status == "PASS"
    assert checks["Display items"].status == "FAIL"
    assert checks["References"].status == "WARNING"


def test_elsevier_highlight_limits():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("elsevier-geomorphology")
    stats = ManuscriptStats(source="highlights.docx", highlight_count=3, highlight_max_characters=86)
    report = audit(stats, profile, path)
    checks = {check.name: check for check in report.checks}
    assert checks["Highlights"].status == "PASS"
    assert checks["Longest highlight"].status == "FAIL"


def test_epsl_letter_checks_length_declarations_and_partial_coverage():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("elsevier-earth-and-planetary-science-letters")
    stats = ManuscriptStats(
        source="letter.tex",
        abstract_words=200,
        body_words=7344,
        section_names=[
            "software environment and data availability",
            "conflict of interest",
        ],
    )

    report = audit(stats, profile, path)
    checks = {check.name: check for check in report.checks}

    assert checks["Profile coverage"].status == "WARNING"
    assert checks["Main text"].actual == 7344
    assert checks["Main text"].status == "FAIL"
    assert checks["Data Availability statement"].status == "PASS"
    assert checks["Competing Interest declaration"].status == "PASS"


def test_geology_hard_limits_and_unmeasured_composite_limit_notice():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("gsa-geology-article")
    stats = ManuscriptStats(
        source="article.docx",
        abstract_words=251,
        figure_count=4,
        table_count=1,
        reference_count=36,
    )
    report = audit(stats, profile, path)
    checks = {check.name: check for check in report.checks}

    assert checks["Abstract"].status == "FAIL"
    assert checks["Display items"].status == "FAIL"
    assert checks["References"].status == "FAIL"
    assert "18,500-character" in checks["Profile coverage"].message


def test_advisory_limits_warn_instead_of_fail():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("aaas-science-advances-research-article")
    stats = ManuscriptStats(
        source="article.tex",
        abstract_words=150,
        body_words=15001,
        figure_count=8,
        table_count=3,
        reference_count=81,
    )
    checks = {check.name: check for check in audit(stats, profile, path).checks}

    assert checks["Main text"].status == "WARNING"
    assert checks["Display items"].status == "WARNING"
    assert checks["References"].status == "WARNING"


def test_basin_research_current_recommendations_warn():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("wiley-basin-research-research-article")
    stats = ManuscriptStats(
        source="article.docx",
        abstract_words=300,
        body_words=8001,
        figure_count=13,
        highlight_count=5,
        highlight_max_characters=101,
        section_names=["Data availability", "Conflict of interest", "Funding"],
    )
    checks = {check.name: check for check in audit(stats, profile, path).checks}

    assert checks["Main text"].status == "WARNING"
    assert checks["Figures"].status == "WARNING"
    assert checks["Highlights"].status == "PASS"
    assert checks["Longest highlight"].status == "FAIL"


def test_egu_profiles_inherit_required_end_matter():
    from texaudit.models import ManuscriptStats

    profile, path = load_profile("egu-solid-earth-research-article")
    stats = ManuscriptStats(
        source="article.tex",
        abstract_words=301,
        section_names=["Data availability", "Author contributions"],
    )
    checks = {check.name: check for check in audit(stats, profile, path).checks}

    assert checks["Abstract"].status == "FAIL"
    assert checks["Data Availability statement"].status == "PASS"
    assert checks["Author Contribution statement"].status == "PASS"
