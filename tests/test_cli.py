from pathlib import Path

from texaudit.audit import audit
from texaudit.parser import parse_manuscript
from texaudit.profiles import load_profile


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


def test_agu_profile_audits_sample():
    fixture = Path(__file__).parent / "fixtures" / "sample.tex"
    profile, path = load_profile("agu-jgr-earth-surface")
    report = audit(parse_manuscript(fixture), profile, path)
    names = {check.name for check in report.checks}
    assert "Publication units" in names
    assert "Abstract" in names


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
